# FastRAG 架构文档

自研 RAG（Retrieval-Augmented Generation）系统，自建 LLM 编排层，不依赖 LangChain / LlamaIndex 等框架。

---

## 目录

- [技术栈](#技术栈)
- [系统架构总览](#系统架构总览)
- [后端架构](#后端架构)
  - [目录结构](#目录结构)
  - [核心领域层（core）](#核心领域层core)
  - [基础设施层（infra）](#基础设施层infra)
  - [API 层（api）](#api-层api)
  - [数据库层（db）](#数据库层db)
  - [配置层（config）](#配置层config)
- [前端架构](#前端架构)
  - [目录结构](#目录结构-1)
  - [路由与页面](#路由与页面)
  - [状态管理](#状态管理)
  - [SSE 流式通信](#sse-流式通信)
- [设计模式](#设计模式)
- [数据流](#数据流)
- [数据库模型](#数据库模型)

---

## 技术栈

| 层 | 技术 |
|---|------|
| Web 框架 | FastAPI 0.115+ (async) |
| 数据库 | PostgreSQL + pgvector 扩展 |
| ORM / 迁移 | SQLAlchemy 2.0 (async) + Alembic |
| 缓存 | Redis (async) |
| LLM 调用 | httpx（OpenAI 兼容协议） |
| 文档解析 | unstructured |
| 关键词检索 | rank-bm25 (BM25Plus) + jieba |
| 重排序 | 百炼 gte-rerank |
| 数据校验 | Pydantic v2 |
| 前端框架 | React 18 + TypeScript |
| 前端构建 | Vite |
| 前端状态 | Zustand |
| 前端 UI | TailwindCSS + shadcn/ui + Radix |
| 前端路由 | React Router v6 |
| 前端 HTTP | Axios |

---

## 系统架构总览

系统采用**分层架构**，严格遵循依赖倒置原则：核心领域层仅依赖 Protocol 抽象接口，不依赖任何基础设施实现。

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (React)                  │
│  ChatPage · Admin Pages · Zustand Stores · SSE      │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP / SSE
┌──────────────────────▼──────────────────────────────┐
│                    API 层 (FastAPI)                   │
│  Routers · Dependencies · Middleware                 │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                  核心领域层 (core)                     │
│  RAGPipeline · IngestionEngine · Protocol 接口       │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                 基础设施层 (infra)                     │
│  LLM · PgVector · Redis · BM25 · Rerank             │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                  数据库层 (db)                        │
│  ORM Models · Repositories · Session Factory         │
└─────────────────────────────────────────────────────┘
```

---

## 后端架构

### 目录结构

```
backend/
├── main.py              # 应用入口：lifespan、CORS、路由注册
├── api/                 # HTTP 层：路由、依赖注入、中间件
│   ├── deps.py          #   依赖注入组合根
│   ├── chat.py          #   SSE 流式对话
│   ├── conversation.py  #   会话 CRUD
│   ├── knowledge.py     #   知识库 CRUD
│   ├── ingestion.py     #   文档入库
│   ├── intent.py        #   意图节点管理
│   ├── trace.py         #   RAG 链路追踪
│   └── mapping.py       #   术语映射 CRUD
├── core/                # 纯领域逻辑，零框架依赖
│   ├── rag/             #   RAG Pipeline（10 步）
│   │   ├── protocols.py #     Protocol 接口定义
│   │   ├── pipeline.py  #     RAGPipeline 编排器
│   │   ├── retrieve.py  #     多通道检索 + RRF 融合
│   │   ├── intent.py    #     LLM 意图分类
│   │   ├── rewrite.py   #     LLM 查询改写
│   │   ├── term_mapper.py #   术语映射扩展
│   │   ├── prompt.py    #     Prompt 构建
│   │   ├── memory.py    #     滑动窗口记忆
│   │   └── tracer.py    #     RAG 链路追踪
│   ├── ingestion/       #   入库 Pipeline（6 节点）
│   │   ├── engine.py    #     IngestionEngine 编排器
│   │   ├── nodes/       #     Pipeline 节点定义
│   │   │   ├── fetcher.py
│   │   │   ├── parser.py
│   │   │   ├── enhancer.py
│   │   │   ├── chunker.py
│   │   │   ├── enricher.py
│   │   │   └── indexer.py
│   │   └── strategies/  #     策略实现
│   │       ├── fetcher/
│   │       ├── parser/
│   │       └── chunker/
│   └── models/          #   Pydantic 领域模型
│       ├── chat.py
│       ├── knowledge.py
│       ├── intent.py
│       ├── ingestion.py
│       └── mapping.py
├── infra/               # 基础设施实现
│   ├── llm/             #   OpenAI 兼容 LLM 客户端
│   ├── vector/          #   PgVector 向量存储
│   ├── cache/           #   Redis 缓存
│   ├── search/          #   BM25 索引与检索
│   └── rerank/          #   百炼 Rerank
├── db/                  # 数据库层
│   ├── models/          #   SQLAlchemy ORM 模型
│   ├── repos/           #   异步 Repository
│   ├── session.py       #   会话工厂
│   └── base.py          #   DeclarativeBase
└── config/              # 配置
    ├── settings.py      #   Pydantic Settings
    └── logging.py       #   日志配置
```

### 核心领域层（core）

核心层遵循**依赖倒置原则**：只依赖 `Protocol` 抽象接口，不 import 任何 infra 或 db 模块。所有具体实现通过构造函数注入。

#### Protocol 接口（`core/rag/protocols.py`）

六个 `@runtime_checkable` Protocol 定义了系统的抽象契约：

| Protocol | 方法 | 唯一实现 |
|---|---|---|
| `LLMProvider` | `stream()`, `chat()`, `embed()`, `close()` | `OpenAICompatClient` |
| `VectorStore` | `search()`, `search_questions()`, `upsert()` | `PgVectorStore` |
| `ConversationMemory` | `load()`, `save()` | `SlidingWindowMemory` |
| `QueryRewriter` | `rewrite()` | `LLMQueryRewriter` |
| `IntentClassifier` | `classify()` | `LLMIntentClassifier` |
| `Reranker` | `rerank()` | `BailianRerankClient` |

#### RAG Pipeline（`core/rag/pipeline.py`）

`RAGPipeline.chat()` 是系统的核心编排器，按顺序执行 10 个步骤：

| 步骤 | 组件 | 说明 |
|------|------|------|
| 1 | `SlidingWindowMemory.load` | 加载会话历史（滑动窗口 + 摘要压缩） |
| 2 | `QueryTermMapper.expand` | 术语映射扩展（正则替换领域缩写） |
| 3 | `LLMQueryRewriter.rewrite` | 查询改写（消解指代与省略） |
| 4 | `LLMIntentClassifier.classify` | 意图分类（路由到知识库） |
| 5 | `MultiChannelRetriever.retrieve` | 多通道检索（向量 + 问题向量 + BM25）+ RRF 融合 |
| 6 | `BailianRerankClient.rerank` | 重排序（可选） |
| 7 | `KnowledgeRepo.batch_get_names` | Source 组装（文档名查找） |
| 8 | `PromptBuilder.build` | Prompt 构建 |
| 9 | `LLMProvider.stream` | LLM 流式生成（支持 Deep Thinking） |
| 10 | `SlidingWindowMemory.save` | 记忆持久化 + 追踪完成 |

**早退出路径**：
- **引导（Guidance）**：意图分类仅命中中置信度匹配时，返回 `GuidanceEvent` 提示用户澄清
- **系统兜底**：无意图匹配时，跳过检索，LLM 直接回答

每个步骤通过 `RagTracer.trace_node()` 记录可观测性数据。

#### 多通道检索（`core/rag/retrieve.py`）

三个检索通道并行执行，结果通过 RRF（Reciprocal Rank Fusion）融合：

| 通道 | 实现 | 检索方式 |
|------|------|---------|
| `VectorSearchChannel` | `PgVectorStore.search` | 向量余弦相似度，按知识库过滤 |
| `QuestionSearchChannel` | `PgVectorStore.search_questions` | 问题向量 → 文档 → 分块（两步检索） |
| `Bm25KeywordChannel` | `Bm25IndexManager.search` | BM25Plus 关键词检索 + jieba 分词 |

**RRF 融合**：K=60，对每个通道的排序结果计算 `1/(K + rank + 1)`，按内容去重后合并得分排序。

#### 入库 Pipeline（`core/ingestion/`）

6 节点固定顺序执行，`IngestionContext` 作为可变状态对象流经各节点：

```
Fetcher → Parser → Enhancer → Chunker → Enricher → Indexer
```

| 节点 | 策略模式 | 可选策略 |
|------|---------|---------|
| `FetcherNode` | 策略字典 | `LocalFileFetcher`、`HttpUrlFetcher` |
| `ParserNode` | 策略字典 | `MarkdownParser`、`UnstructuredParser` |
| `EnhancerNode` | 枚举任务类型 | 上下文补充 / 关键词 / 问题 / 元数据 |
| `ChunkerNode` | 策略字典 | 固定大小 / 段落 / 句子 / 结构感知 |
| `EnricherNode` | 枚举任务类型 | 关键词 / 摘要 / 元数据 |
| `IndexerNode` | 无策略 | Embedding 批量生成 + PgVector upsert + 问题持久化 + BM25 脏标记 |

**结构感知分块器**（`StructureAwareChunker`）：按 Markdown 标题分割，三级尺寸控制（`min_chars`/`target_chars`/`max_chars`），超大段落自动子分块，代码围栏保护不被截断。

### 基础设施层（infra）

| 模块 | 文件 | 实现要点 |
|------|------|---------|
| **LLM** | `infra/llm/client.py` | `OpenAICompatClient`：httpx 异步客户端，兼容 DashScope/SiliconFlow/Ollama。`stream()` SSE 流式，`chat()` 非流式，`embed()` 批量向量化 |
| **LLM SSE** | `infra/llm/stream.py` | `parse_sse_line()`：解析 SSE 行，区分 `delta.content` 和 `delta.reasoning_content` |
| **向量存储** | `infra/vector/pgvector.py` | `PgVectorStore`：pgvector 余弦距离查询，`search()` 分块检索，`search_questions()` 两步检索 |
| **缓存** | `infra/cache/redis.py` | `RedisCache`：`get`/`set`/`set_nx`/`delete`，用于意图节点/术语映射缓存（TTL 7200s）和对话锁（TTL 30s） |
| **BM25** | `infra/search/bm25_index.py` | `Bm25IndexManager`：内存 BM25Plus 索引 + jieba 分词，脏标记模式，按知识库分组 |
| **BM25 通道** | `infra/search/keyword.py` | `Bm25KeywordChannel`：实现 `SearchChannel` Protocol |
| **重排序** | `infra/rerank/bailian.py` | `BailianRerankClient`：百炼 DashScope gte-rerank，可选启用 |

### API 层（api）

#### 依赖注入（`api/deps.py`）

组合根，分两类：

**单例服务**（`@lru_cache`）：

| 工厂方法 | 返回 |
|---------|------|
| `get_settings()` | `Settings` |
| `get_session_factory()` | `async_sessionmaker` |
| `get_llm_provider()` | `OpenAICompatClient`（对话模型） |
| `get_embedding_provider()` | `OpenAICompatClient`（Embedding 模型） |
| `get_vector_store()` | `PgVectorStore` |
| `get_redis_cache()` | `RedisCache` |
| `get_bm25_index_manager()` | `Bm25IndexManager` |
| `get_reranker()` | `BailianRerankClient | None` |

**每请求依赖**（`Depends()`）：

| 工厂方法 | 返回 |
|---------|------|
| `get_db_session()` | `AsyncSession` |
| `get_conversation_repo(session)` | `ConversationRepo` |
| `get_knowledge_repo(session)` | `KnowledgeRepo` |
| `get_trace_repo(session)` | `TraceRepo` |
| `get_intent_repo(session)` | `IntentRepo` |
| `get_mapping_repo(session)` | `MappingRepo`（含 Redis 缓存） |
| `get_ingestion_task_repo(session)` | `IngestionTaskRepo` |

`get_rag_pipeline()` 和 `get_ingestion_engine()` 是两个复杂组装工厂，将所有组件手动连接成完整 Pipeline。

#### 路由

所有路由挂载在 `root_path="/api/fastrag"` 下：

| Router | 前缀 | 核心端点 |
|--------|------|---------|
| `chat` | `/chat` | `POST /stream`（SSE 流式）、`POST /stop` |
| `conversation` | `/conversations` | 会话 CRUD、消息历史、反馈 |
| `knowledge` | `/knowledge-bases` | 知识库 CRUD（级联删除） |
| `ingestion` | 内嵌于 knowledge-bases | 文档上传、入库任务、分块查看 |
| `intent` | `/intent-trees` | 意图节点 CRUD |
| `trace` | `/traces` | RAG 链路追踪 |
| `mapping` | `/query-term-mappings` | 术语映射 CRUD |

**聊天端点要点**：
- `POST /stream`：通过 Redis `set_nx` 获取对话级锁（30s TTL），防止并发请求
- SSE 生成器消费 `RAGPipeline.chat()` 的 `AsyncIterator[ChatEvent]`
- 首轮对话自动通过 LLM 生成标题
- 使用内存 `_task_registry` 跟踪活跃任务，支持 `POST /stop` 取消

**入库端点要点**：
- `POST /documents`：上传文件后通过 `asyncio.create_task()` 异步执行入库 Pipeline
- 返回 202 + `document_id` + `task_id`，前端轮询任务状态

### 数据库层（db）

#### ORM 模型

| 模型 | 表 | 核心字段 |
|------|---|---------|
| `KnowledgeBaseORM` | `knowledge_bases` | id, name(unique), description, ingestion_config(JSON) |
| `KnowledgeDocumentORM` | `knowledge_documents` | id, knowledge_base_id(FK), filename, source_type, status, chunk_count |
| `KnowledgeChunkORM` | `knowledge_chunks` | id, document_id(FK), knowledge_base_id(FK), content, chunk_index, embedding(Vector), metadata\_(JSON) |
| `KnowledgeDocQuestionORM` | `knowledge_doc_questions` | id, document_id(FK), knowledge_base_id(FK), question, embedding(Vector) |
| `QueryTermMappingORM` | `query_term_mappings` | id, source_term, target_term, knowledge_base_id(FK nullable) |
| `ConversationORM` | `conversations` | id, title, created_at, updated_at |
| `MessageORM` | `messages` | id, conversation_id(FK), seq, role, content, sources(JSON), feedback |
| `ConversationSummaryORM` | `conversation_summaries` | id, conversation_id(unique FK), content, summarized_up_to_seq |
| `RagTraceRunORM` | `rag_trace_runs` | id, conversation_id(FK), query, status, total_duration_ms |
| `RagTraceNodeORM` | `rag_trace_nodes` | id, run_id(FK), node_name, status, duration_ms, detail(JSON) |
| `IntentNodeORM` | `intent_nodes` | id, name, intent_type, knowledge_base_id(FK nullable), keywords(JSON), description |
| `IngestionTaskORM` | `ingestion_tasks` | id, knowledge_base_id(FK), document_id(FK), status, node_results(JSON), chunk_count |

#### Repository

所有 Repository 遵循相同模式：构造时接收 `AsyncSession`，方法内使用 SQLAlchemy `select()` 异步查询，立即 commit。

| Repository | 核心方法 |
|-----------|---------|
| `KnowledgeRepo` | 知识库 CRUD（级联删除）、文档 CRUD、分块分页查询、批量名称查找 |
| `ConversationRepo` | 会话 CRUD、消息保存/查询、摘要读写、反馈更新 |
| `TraceRepo` | 追踪运行 CRUD（含 `selectinload` 加载节点） |
| `IntentRepo` | 意图节点 CRUD（写入时刷新 Redis 缓存） |
| `MappingRepo` | 术语映射 CRUD（写入时刷新 Redis 缓存） |
| `IngestionTaskRepo` | 任务创建/更新/失败标记、节点结果追加 |

#### 数据库迁移

Alembic 异步迁移，`env.py` 确保 `vector` 扩展已创建。7 个迁移文件：

| 迁移 | 内容 |
|------|------|
| `0001_initial_schema` | 全部基础表 |
| `0002_add_ingestion_task_chunk_count` | 入库任务增加 chunk_count |
| `0003_retrieval_enhancement` | 新增问题表、术语映射表、分块 metadata |
| `0004_intent_node_kb_link` | 意图节点关联知识库 |
| `0005_drop_intent_node_level_and_parent` | 简化意图节点 |
| `0006_drop_keywords_tsv` | 移除全文搜索列 |
| `0007_add_message_sources` | 消息增加 sources JSON |

### 配置层（config）

使用 `pydantic-settings`，环境变量前缀 `FASTRAG_`，嵌套用 `__` 分隔。核心配置项：

| 配置组 | 变量 | 默认值 |
|--------|------|--------|
| 数据库 | `FASTRAG_DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/fastrag` |
| 缓存 | `FASTRAG_REDIS_URL` | `redis://localhost:6379/0` |
| 日志 | `FASTRAG_LOG_LEVEL` | `INFO` |
| LLM | `FASTRAG_LLM__BASE_URL` / `__CHAT_MODEL` | `http://localhost:11434/v1` / `qwen3:8b` |
| Embedding | `FASTRAG_EMBEDDING__MODEL` / `__DIMENSIONS` | `qwen3-embedding` / `1024` |
| 入库 | `FASTRAG_INGESTION__TASK_TIMEOUT_SECONDS` | `600` |
| BM25 | `FASTRAG_BM25__REBUILD_ON_STARTUP` | `true` |
| Rerank | `FASTRAG_RERANK__MODEL` / `__TOP_N` | `gte-rerank` / `5` |
| RAG | `FASTRAG_RAG_WINDOW_SIZE` / `__SUMMARY_THRESHOLD` / `__RETRIEVAL_TOP_K` | `4` / `5` / `10` |

---

## 前端架构

### 目录结构

```
frontend/src/
├── App.tsx                     # 根组件：ErrorBoundary + RouterProvider + Toast
├── main.tsx                    # 入口
├── router.tsx                  # 路由配置
├── types/
│   └── index.ts                # 全局 TypeScript 类型定义
├── stores/
│   ├── chatStore.ts            # 聊天状态（会话、消息、流式、深度思考）
│   └── themeStore.ts           # 主题状态（亮/暗）
├── hooks/
│   ├── useChat.ts              # chatStore 便捷封装
│   └── useStreamResponse.ts    # SSE 流式客户端
├── services/
│   ├── api.ts                  # Axios 实例（baseURL 从环境变量，60s 超时）
│   ├── chatService.ts          # 停止生成、反馈
│   ├── sessionService.ts       # 会话 CRUD + 消息
│   ├── knowledgeService.ts     # 知识库 + 文档 + 入库 API
│   ├── ragTraceService.ts      # 追踪查看
│   ├── mappingService.ts       # 术语映射 CRUD
│   └── intentTreeService.ts    # 意图节点 CRUD
├── pages/
│   ├── ChatPage.tsx            # 聊天主页
│   ├── NotFoundPage.tsx        # 404
│   └── admin/
│       ├── AdminLayout.tsx     # 管理后台 Shell（侧边栏 + 面包屑 + Outlet）
│       ├── knowledge/          # 知识库管理页面
│       ├── intent-tree/        # 意图树管理页面
│       ├── traces/             # 追踪页面
│       └── mapping/            # 术语映射页面
├── components/
│   ├── chat/                   # 聊天组件（输入框、消息列表、欢迎屏等）
│   ├── layout/                 # 布局组件（主布局、Header、Sidebar）
│   ├── admin/                  # 管理后台组件
│   ├── common/                 # 通用组件（Avatar、Loading、Toast、ErrorBoundary）
│   ├── session/                # 会话列表组件
│   └── ui/                     # shadcn/ui 原语（Button、Card、Dialog 等）
├── lib/
│   └── utils.ts                # cn() 工具（clsx + tailwind-merge）
├── utils/
│   ├── storage.ts              # localStorage 封装
│   ├── helpers.ts              # 通用工具
│   ├── error.ts                # 错误处理
│   └── documentStatus.ts       # 文档状态颜色/标签
└── styles/
    └── globals.css             # Tailwind CSS 全局样式
```

### 路由与页面

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | 重定向到 `/chat` | - |
| `/chat` | `ChatPage` | 新对话 |
| `/chat/:sessionId` | `ChatPage` | 继续对话 |
| `/admin` | `AdminLayout` | 管理后台 Shell |
| `/admin/knowledge` | `KnowledgeListPage` | 知识库列表 |
| `/admin/knowledge/:id/documents` | `KnowledgeDocumentsPage` | 文档管理 |
| `/admin/knowledge/:id/documents/:docId` | `KnowledgeDocumentDetailPage` | 文档详情 |
| `/admin/knowledge/:id/documents/:docId/chunks` | `KnowledgeChunksPage` | 分块查看 |
| `/admin/intent-tree` | `IntentListPage` | 意图节点列表 |
| `/admin/intent-tree/:id/edit` | `IntentEditPage` | 意图节点编辑 |
| `/admin/traces` | `RagTracePage` | 追踪列表 |
| `/admin/traces/:runId` | `RagTraceDetailPage` | 追踪详情 |
| `/admin/mapping` | `MappingPage` | 术语映射管理 |

### 状态管理

`chatStore`（Zustand）管理聊天全部状态：

- **会话管理**：会话列表、当前会话、创建/切换/删除/重命名
- **消息管理**：消息列表、流式内容追加、思考内容追加
- **流式控制**：`sendMessage()` 发起 SSE 流、`cancelGeneration()` 取消（前端 AbortController + 后端 stop）
- **反馈**：`submitFeedback()` 乐观更新 + 失败回滚

### SSE 流式通信

前端 `createStreamResponse()` 使用 `fetch()` + `ReadableStream` 消费 SSE：

| 事件类型 | 处理 |
|---------|------|
| `meta` | 获取 task_id，用于停止请求 |
| `content` | 追加到消息内容 |
| `thinking` | 追加到思考内容（Deep Thinking） |
| `sources` | 显示引用来源 |
| `guidance` | 显示意图引导提示 |
| `done` | 完成流式，更新标题 |

支持 `AbortController` 取消，`combineSignals()` 合并多个中止信号。

---

## 设计模式

### Protocol 接口（结构化类型）

`core/rag/protocols.py` 使用 Python `Protocol` 而非抽象基类。任何具有匹配方法签名的类自动满足协议，无需显式继承。核心层仅依赖这些抽象，实现**依赖倒置**。

### 依赖注入（FastAPI + 手动组合）

两层 DI：
1. **FastAPI `Depends()`**：每请求资源（数据库会话、Repository）
2. **手动组合**：`get_rag_pipeline()` 和 `get_ingestion_engine()` 在工厂函数中手动连接所有组件

单例服务使用 `@lru_cache` 装饰器。

### 策略模式（入库 Pipeline）

`FetcherNode`、`ParserNode`、`ChunkerNode` 使用策略字典：

```python
FetcherNode(strategies={"local": LocalFileFetcher(), "http": HttpUrlFetcher()})
```

运行时根据配置（`source_type`、`parser_type`、`chunker_type`）选择策略。

### Pipeline 模式

两种 Pipeline 实现：
- **RAG Pipeline**：`RAGPipeline.chat()` 顺序执行 10 步，每步带追踪
- **入库 Pipeline**：`IngestionEngine.execute()` 固定 6 步，`IngestionContext` 作为可变状态流经各节点

### Repository 模式

每个领域实体有独立的 Repository 类，封装所有数据库操作。Repository 构造时接收 `AsyncSession`，使用 SQLAlchemy 异步查询 API，将持久化逻辑与业务逻辑分离。

### 脏标记模式（BM25 索引）

`Bm25IndexManager` 使用 `_dirty` 标记：索引新分块时调用 `mark_dirty()`，下次搜索时 `ensure_ready()` 检查并按需重建。避免每次写入都重建索引。

### Cache-Aside 模式（Redis）

`LLMIntentClassifier` 和 `QueryTermMapper` 使用 Redis 作为缓存层：
- **读**：先查 Redis，miss 则查数据库并回填 Redis
- **写**：Repository 变更时使 Redis key 失效

### 事件驱动 SSE 流式

1. `RAGPipeline.chat()` 是 `AsyncIterator[ChatEvent]`，yield 类型化事件
2. 路由的 `_event_stream()` 消费迭代器，序列化为 SSE `data:` 行
3. 前端 `createStreamResponse()` 读取流并分发到类型化处理器

---

## 数据流

### 聊天请求流

```
用户输入
  → chatStore.sendMessage()
    → POST /api/fastrag/chat/stream (SSE)
      → 获取 Redis 锁（set_nx, 30s TTL）
      → RAGPipeline.chat(ChatRequest)
        → 1. SlidingWindowMemory.load（加载历史 + 摘要）
        → 2. QueryTermMapper.expand（正则替换术语）
        → 3. LLMQueryRewriter.rewrite（消解指代）
        → 4. LLMIntentClassifier.classify（LLM 分类）
             → 仅中置信度 → yield GuidanceEvent, return
             → 无匹配 → 跳过检索，LLM 直接回答
        → 5. MultiChannelRetriever.retrieve
             → 预计算 Embedding
             → 并行: VectorSearch / QuestionSearch / BM25
             → RRF 融合
        → 6. BailianRerankClient.rerank（可选）
        → 7. batch_get_names → yield SourcesEvent
        → 8. PromptBuilder.build
        → 9. LLMProvider.stream → yield LLMEvent
        → 10. SlidingWindowMemory.save
      → yield done（首轮生成标题）
    → 释放 Redis 锁
  ← SSE 流消费 → chatStore 更新消息
```

### 文档入库流

```
管理后台上传文件
  → POST /api/fastrag/knowledge-bases/{kb_id}/documents
    → 保存临时文件
    → 创建 KnowledgeDocumentORM (status="pending")
    → 创建 IngestionTaskORM (status="pending")
    → asyncio.create_task(_run())
      → IngestionEngine.execute(config, context, on_node_complete)
        → FetcherNode → raw_content
        → ParserNode → parsed_text
        → EnhancerNode → enhanced_text, keywords, questions
        → ChunkerNode → chunks
        → EnricherNode → chunk.metadata enriched
        → IndexerNode
             → Embedding 批量生成
             → PgVectorStore.upsert
             → 问题持久化
             → Bm25IndexManager.mark_dirty()
      → 更新文档状态为 "completed"
  ← 返回 202 {document_id, task_id}
  ← 前端轮询 GET ingestion-task 获取进度
```

---

## 数据库模型

### ER 关系

```
knowledge_bases 1──N knowledge_documents 1──N knowledge_chunks
                         │                           │
                         └──N knowledge_doc_questions │
                                                         │
intent_nodes ──────────── 可选关联 ─────────── knowledge_bases
query_term_mappings ───── 可选关联 ─────────── knowledge_bases

conversations 1──N messages
conversations 1──1 conversation_summaries
conversations 1──N rag_trace_runs 1──N rag_trace_nodes

ingestion_tasks ──N knowledge_documents
ingestion_tasks ──N knowledge_bases
```

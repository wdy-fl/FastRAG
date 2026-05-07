# FastRAG

自研 RAG（Retrieval-Augmented Generation）系统。自建 LLM 编排层，不依赖 LangChain / LlamaIndex 等框架。

## 技术栈

| 层 | 技术 |
|---|------|
| 后端框架 | FastAPI + Uvicorn |
| 数据库 | PostgreSQL + pgvector |
| 缓存 | Redis |
| ORM / 迁移 | SQLAlchemy 2.0 (async) + Alembic |
| LLM 调用 | httpx（OpenAI 兼容协议） |
| 文档解析 | unstructured |
| 关键词检索 | rank-bm25 (BM25Plus) + jieba |
| 数据校验 | Pydantic v2 |
| 前端 | React + TypeScript + Vite + Tailwind CSS |

## 架构

```
backend/
├── api/            # FastAPI 路由、依赖注入、中间件
├── core/           # 纯领域逻辑，零框架依赖，Protocol 接口
│   ├── rag/        # RAG Pipeline、检索、意图分类、改写、记忆、追踪
│   ├── ingestion/  # 入库 Pipeline（6 节点固定顺序）
│   └── models/     # Pydantic 领域模型
├── infra/          # 基础设施实现（LLM、PgVector、Redis、BM25、Rerank）
├── db/             # SQLAlchemy ORM、异步 Repository、会话工厂
└── config/         # Pydantic Settings + 日志配置

frontend/
├── src/
│   ├── pages/      # 聊天页 + 管理后台（知识库/意图/追踪/术语映射）
│   ├── services/   # 后端 API 调用
│   ├── stores/     # Zustand 状态管理
│   └── components/ # UI 组件
```

## 核心功能

### RAG Pipeline（10 步）

1. 加载会话历史（滑动窗口 + 摘要压缩）
2. 术语映射扩展
3. 查询改写（LLM）
4. 意图分类（LLM）
5. 多通道检索（向量 + 问题向量 + BM25 关键词）+ RRF 融合
6. 重排序（可选，百炼 Rerank）
7. Source 组装（文档名查找）
8. Prompt 构建
9. LLM 流式生成（支持 Deep Thinking）
10. 记忆持久化 + 追踪完成

### 入库 Pipeline（6 节点固定顺序）

```
Fetcher → Parser → Enhancer → Chunker → Enricher → Indexer
```

| 节点 | 可选策略 |
|------|---------|
| Fetcher | 本地文件、HTTP URL |
| Parser | Markdown、Unstructured |
| Enhancer | LLM 文档级增强（上下文补充 / 关键词 / 问题 / 元数据） |
| Chunker | 固定大小、段落、句子、结构感知（代码围栏保护 + 三级尺寸控制） |
| Enricher | LLM 分块级丰富（关键词 / 摘要 / 元数据） |
| Indexer | Embedding 批量生成、pgvector upsert、问题持久化、BM25 脏标记 |

### API 端点

| Router | 前缀 | 功能 |
|--------|------|------|
| chat | `/chat` | SSE 流式对话、停止/取消 |
| conversation | `/conversations` | 会话 CRUD、消息历史、反馈 |
| knowledge | `/knowledge-bases` | 知识库 CRUD（级联删除） |
| ingestion | 内嵌于 knowledge-bases | 文档上传、入库任务状态、分块查看 |
| intent | `/intent-trees` | 意图节点 CRUD |
| trace | `/traces` | RAG 链路追踪（含节点耗时） |
| mapping | `/query-term-mappings` | 术语映射 CRUD |

## 快速开始

### 前置依赖

- Python 3.12+
- PostgreSQL（需安装 pgvector 扩展）
- Redis
- Node.js 18+

### 后端

```bash
cd FastRAG

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -e ".[dev]"

# 配置环境变量
cp .env.example .env
# 编辑 .env，至少配置：
#   FASTRAG_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/fastrag
#   FASTRAG_REDIS_URL=redis://localhost:6379/0
#   FASTRAG_LLM__BASE_URL=http://localhost:11434/v1
#   FASTRAG_LLM__CHAT_MODEL=qwen3:8b
#   FASTRAG_EMBEDDING__BASE_URL=http://localhost:11434/v1
#   FASTRAG_EMBEDDING__MODEL=qwen3-embedding

# 数据库迁移
alembic upgrade head

# 启动服务
uvicorn backend.main:app --reload --port 8000
```

### 前端

```bash
cd FastRAG/frontend

npm install
npm run dev
# 访问 http://localhost:5173
```

## 配置

所有配置通过环境变量设置，前缀为 `FASTRAG_`，嵌套层级用 `__` 分隔。也可使用 `.env` 文件。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `FASTRAG_DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/fastrag` | PostgreSQL 连接串 |
| `FASTRAG_REDIS_URL` | `redis://localhost:6379/0` | Redis 连接串 |
| `FASTRAG_LOG_LEVEL` | `INFO` | 日志级别 |
| `FASTRAG_LLM__BASE_URL` | `http://localhost:11434/v1` | LLM API 地址 |
| `FASTRAG_LLM__API_KEY` | - | LLM API Key |
| `FASTRAG_LLM__CHAT_MODEL` | `qwen3:8b` | 对话模型 |
| `FASTRAG_EMBEDDING__BASE_URL` | `http://localhost:11434/v1` | Embedding API 地址 |
| `FASTRAG_EMBEDDING__API_KEY` | - | Embedding API Key |
| `FASTRAG_EMBEDDING__MODEL` | `qwen3-embedding` | Embedding 模型 |
| `FASTRAG_EMBEDDING__DIMENSIONS` | `1024` | 向量维度 |
| `FASTRAG_RERANK__API_KEY` | - | 百炼 Rerank API Key（可选） |
| `FASTRAG_RERANK__MODEL` | `gte-rerank` | 重排序模型 |
| `FASTRAG_RERANK__TOP_N` | `5` | 重排序返回数量 |
| `FASTRAG_BM25__REBUILD_ON_STARTUP` | `true` | 启动时全量构建 BM25 索引 |
| `FASTRAG_RAG_WINDOW_SIZE` | `4` | 对话历史滑动窗口大小 |
| `FASTRAG_RAG_SUMMARY_THRESHOLD` | `5` | 触发摘要压缩的消息数阈值 |
| `FASTRAG_RAG_RETRIEVAL_TOP_K` | `10` | 检索返回数量 |
| `FASTRAG_INGESTION__TASK_TIMEOUT_SECONDS` | `600` | 入库任务超时时间（秒） |

## 测试

```bash
source .venv/bin/activate
pytest
```

共 28 个测试文件，覆盖单元测试和集成测试。
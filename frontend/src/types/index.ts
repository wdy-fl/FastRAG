// FastRAG 核心类型定义

export type DocumentStatus =
  | "pending"
  | "fetching"
  | "parsing"
  | "chunking"
  | "embedding"
  | "completed"
  | "failed";

export interface Document {
  id: string;
  knowledge_base_id: string;
  filename: string;
  source_type: string;
  source_uri: string;
  status: DocumentStatus;
  chunk_count: number | null;
  created_at: string;
}

// 知识库级摄取配置（对应后端 IngestionConfig Pydantic 模型）
// 注意：后端 IngestionConfig 还包含 fetcher 字段，但路由在触发摄取时
// 会硬编码注入 fetcher（source_type="local", source_uri=临时文件路径），
// 不从 KB 级 ingestion_config 中读取，故前端无需暴露此字段。
export interface IngestionConfig {
  parser?: {
    parser_type?: "unstructured" | "markdown";
  };
  chunker?: {
    chunker_type?: "structure_aware" | "fixed" | "sentence" | "paragraph";
    chunk_size?: number;
    overlap?: number;
    min_chars?: number;
    target_chars?: number;
    max_chars?: number;
  };
  indexer?: {
    batch_size?: number;
  };
  // enhancer/enricher 为 null/undefined 表示禁用，后端无 enabled 字段
  enhancer?: {
    model_id?: string;
    tasks?: Array<{
      type: "context_enhance" | "keywords" | "questions" | "metadata";
    }>;
  } | null;
  enricher?: {
    model_id?: string;
    attach_document_metadata?: boolean;
    tasks?: Array<{
      type: "keywords" | "summary" | "metadata";
    }>;
  } | null;
}

export interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  ingestion_config: IngestionConfig;
  created_at: string;
}

// 摄取任务详情（对应后端 IngestionTaskResponse）
export interface IngestionTaskResponse {
  task_id: string;
  document_id: string;
  status: DocumentStatus;
  started_at: string | null;
  finished_at: string | null;
  chunk_count: number | null;
  error: string | null;
  node_timings: Record<string, number>; // key: 节点名，value: 耗时 ms（仅含成功节点）
}

export interface Chunk {
  id: string;
  chunk_index: number;
  content: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ChunkListResponse {
  total: number;
  page: number;
  page_size: number;
  items: Chunk[];
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  thinking?: string;
  status?: "pending" | "streaming" | "done" | "error" | "cancelled";
  created_at: string;
}

export interface TraceRun {
  id: string;
  conversation_id: string;
  query: string;
  status: "running" | "success" | "failed";
  total_duration_ms: number;
  created_at: string;
}

export interface TraceNode {
  node_name: string;
  status: string;
  duration_ms: number;
  error: string | null;
}

export interface TraceRunDetail extends TraceRun {
  nodes: TraceNode[];
}

export interface IntentNode {
  id: string;
  name: string;
  level: number;
  parent_id: string | null;
  intent_type: string;
  keywords: string[];
  description: string;
}

export interface Mapping {
  id: string;
  source_term: string;
  target_term: string;
  knowledge_base_id: string;
  created_at: string;
}

// 客户端专用（不对应后端模型）
export type FeedbackValue = "like" | "dislike" | null;

export interface ClientMessage extends Message {
  isDeepThinking?: boolean;
  isThinking?: boolean;
  thinkingDurationMs?: number;
  guidance?: unknown;
  feedback?: FeedbackValue;
}

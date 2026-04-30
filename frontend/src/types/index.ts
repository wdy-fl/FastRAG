// FastRAG 核心类型定义

export interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  created_at: string;
}

export interface Document {
  id: string;
  knowledge_base_id: string;
  filename: string;
  source_type: string;
  source_uri: string;
  status: "processing" | "done" | "failed";
  chunk_count: number;
  created_at: string;
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

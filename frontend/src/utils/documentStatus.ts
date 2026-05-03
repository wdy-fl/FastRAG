import type { DocumentStatus } from "../types";

export const STATUS_COLORS: Record<DocumentStatus, string> = {
  pending:   "bg-gray-100 text-gray-600",
  fetching:  "bg-blue-100 text-blue-700",
  parsing:   "bg-blue-100 text-blue-700",
  chunking:  "bg-purple-100 text-purple-700",
  embedding: "bg-indigo-100 text-indigo-700",
  completed: "bg-green-100 text-green-700",
  failed:    "bg-red-100 text-red-700",
};

export const STATUS_LABELS: Record<DocumentStatus, string> = {
  pending:   "待处理",
  fetching:  "获取中",
  parsing:   "解析中",
  chunking:  "分块中",
  embedding: "向量化中",
  completed: "已完成",
  failed:    "失败",
};

export const IN_PROGRESS_STATUSES: DocumentStatus[] = [
  "pending", "fetching", "parsing", "chunking", "embedding",
];

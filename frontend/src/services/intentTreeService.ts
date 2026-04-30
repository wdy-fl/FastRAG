import api from "./api";
import type { IntentNode } from "../types";

const BASE = "/api/fastrag/intent-trees";

export const intentTreeService = {
  listNodes: (): Promise<{ data: IntentNode[] }> => api.get(`${BASE}/nodes`),

  createNode: (data: Omit<IntentNode, "id">): Promise<{ data: IntentNode }> =>
    api.post(`${BASE}/nodes`, data),

  updateNode: (id: string, data: Partial<IntentNode>): Promise<{ data: IntentNode }> =>
    api.put(`${BASE}/nodes/${id}`, data),

  deleteNode: (id: string): Promise<void> => api.delete(`${BASE}/nodes/${id}`),
};

import api from "./api";
import type { KnowledgeBase, Document, IngestionTaskResponse, IngestionConfig } from "../types";

const BASE = "/api/fastrag/knowledge-bases";

export const knowledgeService = {
  listKnowledgeBases: (): Promise<{ data: KnowledgeBase[] }> => api.get(BASE),

  createKnowledgeBase: (data: { name: string; description: string }): Promise<{ data: KnowledgeBase }> =>
    api.post(BASE, data),

  updateKnowledgeBase: (
    id: string,
    body: { name?: string; description?: string; ingestion_config?: IngestionConfig }
  ): Promise<{ data: KnowledgeBase }> =>
    api.patch(`${BASE}/${id}`, body),

  deleteKnowledgeBase: (id: string): Promise<void> => api.delete(`${BASE}/${id}`),

  listDocuments: (kbId: string): Promise<{ data: Document[] }> =>
    api.get(`${BASE}/${kbId}/documents`),

  deleteDocument: (kbId: string, docId: string): Promise<void> =>
    api.delete(`${BASE}/${kbId}/documents/${docId}`),

  uploadDocument: (
    kbId: string,
    file: File
  ): Promise<{ data: { document_id: string; task_id: string; status: string } }> => {
    const form = new FormData();
    form.append("file", file);
    return api.post(`${BASE}/${kbId}/documents`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  getIngestionTask: (
    kbId: string,
    docId: string
  ): Promise<{ data: IngestionTaskResponse }> =>
    api.get(`${BASE}/${kbId}/documents/${docId}/ingestion-task`),
};

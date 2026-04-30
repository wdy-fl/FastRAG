import api from "./api";
import type { KnowledgeBase, Document } from "../types";

const BASE = "/api/fastrag/knowledge-bases";

export const knowledgeService = {
  listKnowledgeBases: (): Promise<{ data: KnowledgeBase[] }> => api.get(BASE),

  createKnowledgeBase: (data: { name: string; description: string }): Promise<{ data: KnowledgeBase }> =>
    api.post(BASE, data),

  deleteKnowledgeBase: (id: string): Promise<void> => api.delete(`${BASE}/${id}`),

  listDocuments: (kbId: string): Promise<{ data: Document[] }> =>
    api.get(`${BASE}/${kbId}/documents`),

  uploadDocument: (
    kbId: string,
    params: {
      file: File;
      parser_type: string;
      chunker_type: string;
      chunk_size: number;
      overlap: number;
    }
  ): Promise<{ data: Document }> => {
    const form = new FormData();
    form.append("file", params.file);
    form.append("parser_type", params.parser_type);
    form.append("chunker_type", params.chunker_type);
    form.append("chunk_size", String(params.chunk_size));
    form.append("overlap", String(params.overlap));
    return api.post(`${BASE}/${kbId}/documents`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
};

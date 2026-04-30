import api from "./api";
import type { Mapping } from "../types";

const BASE = "/api/fastrag/query-term-mappings";

export const mappingService = {
  list: (): Promise<{ data: Mapping[] }> => api.get(BASE),

  create: (data: Pick<Mapping, "source_term" | "target_term" | "knowledge_base_id">): Promise<{ data: Mapping }> =>
    api.post(BASE, data),

  delete: (id: string): Promise<void> => api.delete(`${BASE}/${id}`),
};

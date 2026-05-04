import api from "./api";
import type { TraceRun, TraceRunDetail } from "../types";

const BASE = "/api/fastrag/traces";

export const ragTraceService = {
  listRuns: (): Promise<{ data: TraceRun[] }> => api.get(BASE),

  getRun: (runId: string): Promise<{ data: TraceRunDetail }> => api.get(`${BASE}/${runId}`),
};

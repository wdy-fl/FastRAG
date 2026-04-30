import api from "./api";
import type { TraceRun } from "../types";

const BASE = "/api/fastrag/traces";

export const ragTraceService = {
  listRuns: (): Promise<{ data: TraceRun[] }> => api.get(BASE),

  getRun: (runId: string): Promise<{ data: TraceRun }> => api.get(`${BASE}/${runId}`),
};

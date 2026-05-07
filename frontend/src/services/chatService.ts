import api from "./api";

const BASE = "/api/fastrag/chat";

export const chatService = {
  stopTask: (taskId: string): Promise<void> =>
    api.post(`${BASE}/stop`, { task_id: taskId }),

  submitFeedback: (messageId: string, rating: "up" | "down" | null): Promise<void> =>
    api.post(`/api/fastrag/conversations/messages/${messageId}/feedback`, { rating }),
};

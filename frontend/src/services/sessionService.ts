import api from "./api";
import type { Conversation, Message } from "../types";

const BASE = "/api/fastrag/conversations";

export const sessionService = {
  list: (): Promise<{ data: Conversation[] }> => api.get(BASE),

  get: (id: string): Promise<{ data: Conversation }> => api.get(`${BASE}/${id}`),

  create: (title?: string): Promise<{ data: Conversation }> =>
    api.post(BASE, { title: title ?? "新对话" }),

  delete: (id: string): Promise<void> => api.delete(`${BASE}/${id}`),

  update: (id: string, title: string): Promise<{ data: Conversation }> =>
    api.put(`${BASE}/${id}`, { title }),

  getMessages: (id: string): Promise<{ data: Message[] }> =>
    api.get(`${BASE}/${id}/messages`),
};

import { create } from "zustand";
import { toast } from "sonner";

import type { Conversation, ClientMessage, FeedbackValue } from "@/types";
import { sessionService } from "@/services/sessionService";
import { chatService } from "@/services/chatService";
import { createStreamResponse } from "@/hooks/useStreamResponse";

// UI-only session shape derived from Conversation
interface Session {
  id: string;
  title: string;
  lastTime?: string;
}

interface ChatState {
  sessions: Session[];
  currentSessionId: string | null;
  messages: ClientMessage[];
  isLoading: boolean;
  sessionsLoaded: boolean;
  inputFocusKey: number;
  isStreaming: boolean;
  isCreatingNew: boolean;
  deepThinkingEnabled: boolean;
  thinkingStartAt: number | null;
  streamTaskId: string | null;
  streamAbort: (() => void) | null;
  streamingMessageId: string | null;
  cancelRequested: boolean;
  fetchSessions: () => Promise<void>;
  createSession: () => Promise<string>;
  deleteSession: (sessionId: string) => Promise<void>;
  renameSession: (sessionId: string, title: string) => Promise<void>;
  selectSession: (sessionId: string) => Promise<void>;
  updateSessionTitle: (sessionId: string, title: string) => void;
  setDeepThinkingEnabled: (enabled: boolean) => void;
  sendMessage: (content: string) => Promise<void>;
  cancelGeneration: () => Promise<void>;
  appendStreamContent: (delta: string) => void;
  appendThinkingContent: (delta: string) => void;
  finalizeStreamMessage: (msgId: string) => void;
  setMessageError: (msgId: string, errorMsg: string) => void;
  submitFeedback: (messageId: string, feedback: FeedbackValue) => Promise<void>;
}

function conversationToSession(conv: Conversation): Session {
  return {
    id: conv.id,
    title: conv.title || "新对话",
    lastTime: conv.updated_at,
  };
}

function computeThinkingDuration(startAt?: number | null) {
  if (!startAt) return undefined;
  const seconds = Math.round((Date.now() - startAt) / 1000);
  return Math.max(1, seconds);
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: [],
  currentSessionId: null,
  messages: [],
  isLoading: false,
  sessionsLoaded: false,
  inputFocusKey: 0,
  isStreaming: false,
  isCreatingNew: false,
  deepThinkingEnabled: false,
  thinkingStartAt: null,
  streamTaskId: null,
  streamAbort: null,
  streamingMessageId: null,
  cancelRequested: false,

  fetchSessions: async () => {
    const { isLoading, sessionsLoaded } = get();
    if (isLoading || sessionsLoaded) return;
    set({ isLoading: true });
    try {
      const res = await sessionService.list();
      const sessions: Session[] = (res.data ?? [])
        .map(conversationToSession)
        .sort((a, b) => {
          const timeA = a.lastTime ? new Date(a.lastTime).getTime() : 0;
          const timeB = b.lastTime ? new Date(b.lastTime).getTime() : 0;
          return timeB - timeA;
        });
      set({ sessions });
    } catch (error) {
      toast.error((error as Error).message || "加载会话失败");
    } finally {
      set({ isLoading: false, sessionsLoaded: true });
    }
  },

  createSession: async () => {
    const state = get();
    if (state.messages.length === 0 && !state.currentSessionId) {
      set({
        isCreatingNew: true,
        isLoading: false,
        thinkingStartAt: null,
        deepThinkingEnabled: false,
      });
      return "";
    }
    if (state.isStreaming) {
      await get().cancelGeneration();
    }
    set({
      currentSessionId: null,
      messages: [],
      isStreaming: false,
      isLoading: false,
      isCreatingNew: true,
      deepThinkingEnabled: false,
      thinkingStartAt: null,
      streamTaskId: null,
      streamAbort: null,
      streamingMessageId: null,
      cancelRequested: false,
    });
    return "";
  },

  deleteSession: async (sessionId) => {
    try {
      await sessionService.delete(sessionId);
      set((state) => ({
        sessions: state.sessions.filter((session) => session.id !== sessionId),
        messages: state.currentSessionId === sessionId ? [] : state.messages,
        currentSessionId:
          state.currentSessionId === sessionId ? null : state.currentSessionId,
      }));
      toast.success("删除成功");
    } catch (error) {
      toast.error((error as Error).message || "删除会话失败");
    }
  },

  renameSession: async (sessionId, title) => {
    const nextTitle = title.trim();
    if (!nextTitle) return;
    try {
      await sessionService.update(sessionId, nextTitle);
      set((state) => ({
        sessions: state.sessions.map((session) =>
          session.id === sessionId ? { ...session, title: nextTitle } : session
        ),
      }));
      toast.success("已重命名");
    } catch (error) {
      toast.error((error as Error).message || "重命名失败");
    }
  },

  selectSession: async (sessionId) => {
    if (!sessionId) return;
    if (get().currentSessionId === sessionId && get().messages.length > 0) return;
    if (get().isStreaming) {
      await get().cancelGeneration();
    }
    set({
      isLoading: true,
      currentSessionId: sessionId,
      isCreatingNew: false,
      thinkingStartAt: null,
    });
    try {
      const res = await sessionService.getMessages(sessionId);
      if (get().currentSessionId !== sessionId) return;
      const mapped: ClientMessage[] = (res.data ?? []).map((item) => ({
        ...item,
        isDeepThinking: false,
        isThinking: false,
        status: "done" as const,
      })) as ClientMessage[];
      set({ messages: mapped });
    } catch (error) {
      toast.error((error as Error).message || "加载消息失败");
    } finally {
      if (get().currentSessionId !== sessionId) {
        set({ isLoading: false });
        return;
      }
      set({
        isLoading: false,
        isStreaming: false,
        streamTaskId: null,
        streamAbort: null,
        streamingMessageId: null,
        cancelRequested: false,
      });
    }
  },

  updateSessionTitle: (sessionId, title) => {
    set((state) => ({
      sessions: state.sessions.map((session) =>
        session.id === sessionId ? { ...session, title } : session
      ),
    }));
  },

  setDeepThinkingEnabled: (enabled) => {
    set({ deepThinkingEnabled: enabled });
  },

  sendMessage: async (content) => {
    const trimmed = content.trim();
    if (!trimmed) return;
    if (get().isStreaming) return;

    const deepThinkingEnabled = get().deepThinkingEnabled;
    const inputFocusKey = Date.now();

    // 如果没有当前会话，先创建
    let convId = get().currentSessionId;
    if (!convId) {
      try {
        const res = await sessionService.create();
        convId = res.data.id;
        set((s) => ({
          currentSessionId: convId,
          isCreatingNew: false,
          sessions: [conversationToSession(res.data), ...s.sessions],
        }));
      } catch (error) {
        toast.error((error as Error).message || "创建会话失败");
        return;
      }
    }

    const now = new Date().toISOString();
    const userMessage: ClientMessage = {
      id: `user-${Date.now()}`,
      conversation_id: convId,
      role: "user",
      content: trimmed,
      status: "done",
      created_at: now,
    };
    const streamingMsgId = `assistant-${Date.now()}`;
    const assistantMessage: ClientMessage = {
      id: streamingMsgId,
      conversation_id: convId,
      role: "assistant",
      content: "",
      thinking: deepThinkingEnabled ? "" : undefined,
      isDeepThinking: deepThinkingEnabled,
      isThinking: deepThinkingEnabled,
      status: "streaming",
      created_at: now,
    };

    set((state) => ({
      messages: [...state.messages, userMessage, assistantMessage],
      isStreaming: true,
      streamingMessageId: streamingMsgId,
      thinkingStartAt: deepThinkingEnabled ? Date.now() : null,
      inputFocusKey,
      streamTaskId: null,
      cancelRequested: false,
    }));

    const { start, cancel } = createStreamResponse(
      {
        url: `${API_BASE_URL}/api/fastrag/chat/stream`,
        body: {
          query: trimmed,
          conversation_id: convId,
          deep_thinking: deepThinkingEnabled,
        },
      },
      {
        onMeta: ({ task_id }) => {
          set({ streamTaskId: task_id });
        },
        onMessage: ({ content: delta }) => {
          get().appendStreamContent(delta);
        },
        onThinking: ({ content: delta }) => {
          get().appendThinkingContent(delta);
        },
        onSources: ({ sources }) => {
          set((s) => ({
            messages: s.messages.map((m) =>
              m.id === streamingMsgId ? { ...m, sources } : m
            ),
          }));
        },
        onGuidance: ({ intent }) => {
          set((s) => ({
            messages: s.messages.map((m) =>
              m.id === streamingMsgId ? { ...m, guidance: intent } : m
            ),
          }));
        },
        onDone: ({ title }) => {
          if (title && convId) {
            set((s) => ({
              sessions: s.sessions.map((sess) =>
                sess.id === convId ? { ...sess, title } : sess
              ),
            }));
          }
          get().finalizeStreamMessage(streamingMsgId);
          set({
            isStreaming: false,
            streamTaskId: null,
            streamAbort: null,
            streamingMessageId: null,
            thinkingStartAt: null,
            cancelRequested: false,
          });
        },
        onError: (err) => {
          get().setMessageError(streamingMsgId, err.message);
          set({
            isStreaming: false,
            streamTaskId: null,
            streamAbort: null,
            streamingMessageId: null,
            thinkingStartAt: null,
            cancelRequested: false,
          });
          toast.error(err.message || "生成失败");
        },
      }
    );

    set({ streamAbort: cancel });

    try {
      await start();
    } catch (error) {
      if ((error as Error).name === "AbortError") return;
      get().setMessageError(streamingMsgId, (error as Error).message || "生成失败");
      set({
        isStreaming: false,
        streamTaskId: null,
        streamAbort: null,
        streamingMessageId: null,
        thinkingStartAt: null,
        cancelRequested: false,
      });
    } finally {
      // 如果 onDone/onError 没有清理（极端情况），在此兜底
      if (get().streamingMessageId === streamingMsgId) {
        set({
          isStreaming: false,
          streamTaskId: null,
          streamAbort: null,
          streamingMessageId: null,
          cancelRequested: false,
        });
      }
    }
  },

  cancelGeneration: async () => {
    const { streamTaskId, streamAbort } = get();
    streamAbort?.(); // 前端立即停止接收
    if (streamTaskId) {
      await chatService.stopTask(streamTaskId).catch(() => {});
    }
    set((state) => ({
      cancelRequested: false,
      isStreaming: false,
      streamTaskId: null,
      streamAbort: null,
      // 将正在流式的消息标记为 cancelled
      messages: state.messages.map((m) => {
        if (m.id !== state.streamingMessageId) return m;
        const suffix = m.content.includes("（已停止生成）") ? "" : "\n\n（已停止生成）";
        return {
          ...m,
          content: m.content + suffix,
          status: "cancelled" as const,
          isThinking: false,
          thinkingDurationMs:
            m.thinkingDurationMs ?? computeThinkingDuration(state.thinkingStartAt),
        };
      }),
      streamingMessageId: null,
      thinkingStartAt: null,
    }));
  },

  appendStreamContent: (delta) => {
    if (!delta) return;
    set((state) => {
      const shouldFinalizeThinking = state.thinkingStartAt != null;
      const duration = computeThinkingDuration(state.thinkingStartAt);
      return {
        thinkingStartAt: shouldFinalizeThinking ? null : state.thinkingStartAt,
        messages: state.messages.map((message) => {
          if (message.id !== state.streamingMessageId) return message;
          if (message.status === "cancelled" || message.status === "error") return message;
          return {
            ...message,
            content: message.content + delta,
            isThinking: shouldFinalizeThinking ? false : message.isThinking,
            thinkingDurationMs:
              shouldFinalizeThinking && !message.thinkingDurationMs
                ? duration
                : message.thinkingDurationMs,
          };
        }),
      };
    });
  },

  appendThinkingContent: (delta) => {
    if (!delta) return;
    set((state) => ({
      thinkingStartAt: state.thinkingStartAt ?? Date.now(),
      messages: state.messages.map((message) =>
        message.id === state.streamingMessageId &&
        message.status !== "cancelled" &&
        message.status !== "error"
          ? {
              ...message,
              thinking: `${message.thinking ?? ""}${delta}`,
              isThinking: true,
            }
          : message
      ),
    }));
  },

  finalizeStreamMessage: (msgId) => {
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === msgId
          ? {
              ...m,
              status: "done" as const,
              isThinking: false,
              thinkingDurationMs:
                m.thinkingDurationMs ?? computeThinkingDuration(state.thinkingStartAt),
            }
          : m
      ),
    }));
  },

  setMessageError: (msgId, errorMsg) => {
    void errorMsg; // 错误消息已通过 toast 展示，这里仅更新状态
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === msgId
          ? {
              ...m,
              status: "error" as const,
              isThinking: false,
              thinkingDurationMs:
                m.thinkingDurationMs ?? computeThinkingDuration(state.thinkingStartAt),
            }
          : m
      ),
    }));
  },

  submitFeedback: async (messageId, feedback) => {
    const rating = feedback === "like" ? "up" : feedback === "dislike" ? "down" : null;
    const prev = get().messages.find((m) => m.id === messageId);
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === messageId ? { ...m, feedback } : m
      ),
    }));
    if (!rating) {
      toast.success("取消成功");
      return;
    }
    try {
      await chatService.submitFeedback(messageId, rating);
      toast.success(feedback === "like" ? "点赞成功" : "点踩成功");
    } catch (error) {
      // 回滚
      const prevFeedback = prev?.feedback ?? null;
      set((state) => ({
        messages: state.messages.map((m) =>
          m.id === messageId ? { ...m, feedback: prevFeedback } : m
        ),
      }));
      toast.error((error as Error).message || "反馈保存失败");
    }
  },
}));

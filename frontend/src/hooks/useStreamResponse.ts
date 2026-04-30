export interface StreamMetaPayload {
  task_id: string;
}

export interface MessagePayload {
  content: string;
}

export interface GuidancePayload {
  intent: unknown;
}

export interface DonePayload {
  title: string;
}

export interface StreamHandlers {
  onMeta?: (payload: StreamMetaPayload) => void;
  onMessage?: (payload: MessagePayload) => void;
  onThinking?: (payload: MessagePayload) => void;
  onGuidance?: (payload: GuidancePayload) => void;
  onDone?: (payload: DonePayload) => void;
  onError?: (error: Error) => void;
}

export interface StreamOptions {
  url: string;
  body: Record<string, unknown>;
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

export function createStreamResponse(
  options: StreamOptions,
  handlers: StreamHandlers
): { start: () => Promise<void>; cancel: () => void } {
  const controller = new AbortController();
  const signal = options.signal
    ? combineSignals(options.signal, controller.signal)
    : controller.signal;

  async function start() {
    let response: Response;
    try {
      response = await fetch(options.url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
          ...(options.headers ?? {}),
        },
        body: JSON.stringify(options.body),
        signal,
      });
    } catch (e) {
      handlers.onError?.(e instanceof Error ? e : new Error(String(e)));
      return;
    }

    if (!response.ok || !response.body) {
      handlers.onError?.(new Error(`HTTP ${response.status}`));
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split(/\r?\n/);
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data:")) continue;
          const raw = line.slice(5).trim();
          if (!raw || raw === "[DONE]") continue;
          try {
            const payload = JSON.parse(raw);
            dispatchEvent(payload, handlers);
          } catch {
            // 忽略非 JSON 行
          }
        }
      }
    } catch (e) {
      if (!(e instanceof DOMException && e.name === "AbortError")) {
        handlers.onError?.(e instanceof Error ? e : new Error(String(e)));
      }
    } finally {
      reader.releaseLock();
    }
  }

  function cancel() {
    controller.abort();
  }

  return { start, cancel };
}

function dispatchEvent(payload: Record<string, unknown>, handlers: StreamHandlers) {
  switch (payload.type) {
    case "meta":
      handlers.onMeta?.({ task_id: payload.task_id as string });
      break;
    case "content":
      handlers.onMessage?.({ content: payload.content as string });
      break;
    case "thinking":
      handlers.onThinking?.({ content: payload.content as string });
      break;
    case "guidance":
      handlers.onGuidance?.({ intent: payload.intent });
      break;
    case "done":
      handlers.onDone?.({ title: (payload.title as string) ?? "" });
      break;
  }
}

function combineSignals(...signals: AbortSignal[]): AbortSignal {
  const controller = new AbortController();
  for (const signal of signals) {
    if (signal.aborted) {
      controller.abort();
      break;
    }
    signal.addEventListener("abort", () => controller.abort(), { once: true });
  }
  return controller.signal;
}

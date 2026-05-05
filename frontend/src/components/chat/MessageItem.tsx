import * as React from "react";
import { Brain, ChevronDown, FileText, HelpCircle } from "lucide-react";

import { FeedbackButtons } from "@/components/chat/FeedbackButtons";
import { MarkdownRenderer } from "@/components/chat/MarkdownRenderer";
import { ThinkingIndicator } from "@/components/chat/ThinkingIndicator";
import { cn } from "@/lib/utils";
import type { ClientMessage } from "@/types";

interface GuidanceIntent {
  needs_guidance?: boolean;
  guidance_message?: string;
  candidates?: Array<{ id: string; name: string; description?: string }>;
}

interface MessageItemProps {
  message: ClientMessage;
  isLast?: boolean;
}

export const MessageItem = React.memo(function MessageItem({ message, isLast }: MessageItemProps) {
  const isUser = message.role === "user";
  const showFeedback =
    message.role === "assistant" &&
    message.status !== "streaming" &&
    message.id &&
    !message.id.startsWith("assistant-");
  const isThinking = Boolean(message.isThinking);
  const [thinkingExpanded, setThinkingExpanded] = React.useState(false);
  const hasThinking = Boolean(message.thinking && message.thinking.trim().length > 0);
  const hasContent = message.content.trim().length > 0;
  const hasSources = Boolean(message.sources && message.sources.length > 0);
  const [sourcesExpanded, setSourcesExpanded] = React.useState(false);
  const isWaiting = message.status === "streaming" && !isThinking && !hasContent;
  const guidance = message.guidance as GuidanceIntent | undefined;
  const hasGuidance = Boolean(guidance?.needs_guidance);

  if (isUser) {
    return (
      <div className="flex">
        <div className="user-message">
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        </div>
      </div>
    );
  }

  const thinkingDuration = message.thinkingDurationMs
    ? `${Math.round(message.thinkingDurationMs)}秒`
    : "";
  return (
    <div className="group flex">
      <div className="min-w-0 flex-1 space-y-4">
        {isThinking ? (
          <ThinkingIndicator content={message.thinking} duration={message.thinkingDurationMs} />
        ) : null}
        {!isThinking && hasThinking ? (
          <div className="overflow-hidden rounded-lg border border-[#BFDBFE] bg-[#DBEAFE]">
            <button
              type="button"
              onClick={() => setThinkingExpanded((prev) => !prev)}
              className="flex w-full items-center gap-2 px-4 py-3 text-left transition-colors hover:bg-[#BFDBFE]/30"
            >
              <div className="flex flex-1 items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#BFDBFE]">
                  <Brain className="h-4 w-4 text-[#2563EB]" />
                </div>
                <span className="text-sm font-medium text-[#2563EB]">深度思考</span>
                {thinkingDuration ? (
                  <span className="rounded-full bg-[#BFDBFE] px-2 py-0.5 text-xs text-[#2563EB]">
                    {thinkingDuration}
                  </span>
                ) : null}
              </div>
              <ChevronDown
                className={cn(
                  "h-4 w-4 text-[#3B82F6] transition-transform",
                  thinkingExpanded && "rotate-180"
                )}
              />
            </button>
            {thinkingExpanded ? (
              <div className="border-t border-[#BFDBFE] px-4 pb-4">
                <div className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-[#1E40AF]">
                  {message.thinking}
                </div>
              </div>
            ) : null}
          </div>
        ) : null}
        <div className="space-y-2">
          {isWaiting ? (
            <div className="ai-wait" aria-label="思考中">
              <span className="ai-wait-dots" aria-hidden="true">
                <span className="ai-wait-dot" />
                <span className="ai-wait-dot" />
                <span className="ai-wait-dot" />
              </span>
            </div>
          ) : null}
          {hasGuidance ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
              <div className="flex items-start gap-2">
                <HelpCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
                <div className="space-y-2">
                  <p className="text-sm text-amber-800">
                    {guidance?.guidance_message || "请进一步明确您的问题。"}
                  </p>
                  {guidance?.candidates && guidance.candidates.length > 0 ? (
                    <ul className="space-y-1">
                      {guidance.candidates.map((c) => (
                        <li key={c.id} className="text-sm text-amber-700">
                          · {c.name}{c.description ? `：${c.description}` : ""}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              </div>
            </div>
          ) : null}
          {hasContent ? <MarkdownRenderer content={message.content} /> : null}
          {hasSources ? (
            <div className="overflow-hidden rounded-lg border border-gray-200 bg-gray-50">
              <button
                type="button"
                onClick={() => setSourcesExpanded((prev) => !prev)}
                className="flex w-full items-center gap-2 px-4 py-2.5 text-left transition-colors hover:bg-gray-100"
              >
                <FileText className="h-4 w-4 text-gray-500" />
                <span className="text-sm font-medium text-gray-700">
                  引用来源 ({message.sources!.length})
                </span>
                <ChevronDown
                  className={cn(
                    "ml-auto h-4 w-4 text-gray-400 transition-transform",
                    sourcesExpanded && "rotate-180"
                  )}
                />
              </button>
              {sourcesExpanded ? (
                <div className="border-t border-gray-200 px-4 pb-3">
                  <ul className="mt-2 space-y-2">
                    {message.sources!.map((s) => (
                      <li key={s.ref} className="text-sm text-gray-600">
                        <span className="mr-1 inline-flex h-5 w-5 items-center justify-center rounded bg-gray-200 text-xs font-medium text-gray-700">
                          {s.ref}
                        </span>
                        {s.document_name ? (
                          <span className="font-medium text-gray-800">{s.document_name}</span>
                        ) : null}
                        <span className="ml-2 text-xs text-gray-400">
                          相关度 {(s.score * 100).toFixed(1)}%
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          ) : null}
          {message.status === "error" ? (
            <p className="text-xs text-rose-500">生成已中断。</p>
          ) : null}
          {showFeedback ? (
            <FeedbackButtons
              messageId={message.id}
              feedback={message.feedback ?? null}
              content={message.content}
              alwaysVisible={Boolean(isLast)}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
});

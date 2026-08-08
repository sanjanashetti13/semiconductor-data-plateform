import type { ChatMessage as ChatMessageType } from "@/types";
import { Button } from "@/components/ui/button";
import { toBusinessAnswer } from "@/lib/displayAnswer";
import { cn } from "@/lib/utils";
import { Check, ChevronDown, Copy, RotateCcw } from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ChatMessageProps {
  message: ChatMessageType;
  developerMode?: boolean;
  onRetry?: () => void;
  onFollowUp?: (prompt: string) => void;
}

function formatModel(model?: string): string {
  if (!model) return "—";
  if (model.includes("llama-3.3-70b")) return "Llama 3.3 70B";
  return model;
}

function formatRouterDecision(value?: string | null): string {
  if (!value) return "—";
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function ChatMessage({
  message,
  developerMode = false,
  onRetry,
  onFollowUp,
}: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const isUser = message.role === "user";
  const followUps = message.error
    ? message.suggestions ?? []
    : message.followUps ?? [];

  const displayContent = isUser
    ? message.content
    : developerMode
      ? message.content
      : toBusinessAnswer(message.content);

  const hasTechnicalDetails =
    !isUser &&
    !message.error &&
    developerMode &&
    Boolean(
      message.sql ||
        message.tool ||
        message.toolLabel ||
        message.model ||
        typeof message.executionTime === "number" ||
        message.routerDecision ||
        message.category ||
        message.validationResult ||
        (message.agentsUsed && message.agentsUsed.length > 0) ||
        message.plannerRationale ||
        (message.executionGraph && message.executionGraph.length > 0),
    );

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(displayContent);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1400);
    } catch {
      // ignore
    }
  }

  return (
    <div
      className={cn(
        "mx-auto flex w-full max-w-3xl gap-3 px-4",
        isUser ? "justify-end" : "justify-start",
      )}
    >
      <div
        className={cn(
          "max-w-[min(100%,42rem)] text-sm leading-relaxed",
          isUser
            ? "rounded-full bg-zinc-600 px-5 py-2.5 text-white shadow-[0_0_24px_rgba(113,113,122,0.35)]"
            : cn(
                "rounded-2xl border bg-[#07111f]/80 px-4 py-3.5 text-zinc-100 shadow-[0_0_32px_rgba(34,211,238,0.12)] backdrop-blur-md",
                message.error
                  ? "border-rose-400/40"
                  : "border-cyan-400/35",
              ),
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div
            className={cn(
              message.error &&
                "border-l-2 border-rose-500 pl-3 text-zinc-200",
            )}
          >
            <div className="prose prose-invert prose-sm max-w-none prose-headings:mt-4 prose-headings:mb-2 prose-headings:text-zinc-50 prose-p:my-2 prose-li:my-0.5 prose-pre:rounded-xl prose-pre:border prose-pre:border-cyan-500/20 prose-pre:bg-[#020617]/80 prose-code:text-sky-300">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {displayContent}
              </ReactMarkdown>
            </div>
          </div>
        )}

        {hasTechnicalDetails && (
          <div className="mt-3 rounded-xl border border-cyan-500/20 bg-[#020617]/60">
            <button
              type="button"
              className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-xs text-zinc-400 transition hover:text-zinc-200"
              onClick={() => setDetailsOpen((open) => !open)}
              aria-expanded={detailsOpen}
            >
              <span className="font-medium tracking-wide">Technical Details</span>
              <ChevronDown
                className={cn(
                  "h-4 w-4 transition",
                  detailsOpen ? "rotate-180" : "rotate-0",
                )}
              />
            </button>
            {detailsOpen && (
              <div className="space-y-3 border-t border-cyan-500/15 px-3 py-3 text-xs text-zinc-300">
                <DetailRow
                  label="Router Decision"
                  value={formatRouterDecision(
                    message.routerDecision ?? message.category,
                  )}
                />
                {message.agentsUsed && message.agentsUsed.length > 0 && (
                  <DetailRow
                    label="Agents Used"
                    value={message.agentsUsed.join(" → ")}
                  />
                )}
                {message.plannerRationale && (
                  <DetailRow
                    label="Planner"
                    value={message.plannerRationale}
                  />
                )}
                {message.executionGraph && message.executionGraph.length > 0 && (
                  <DetailRow
                    label="Execution Graph"
                    value={message.executionGraph.join(" → ")}
                  />
                )}
                <DetailRow
                  label="Tool Used"
                  value={message.toolLabel ?? message.tool ?? "—"}
                />
                <DetailRow label="Model Used" value={formatModel(message.model)} />
                <DetailRow
                  label="Execution Time"
                  value={
                    typeof message.executionTime === "number"
                      ? `${message.executionTime.toFixed(2)}s`
                      : "—"
                  }
                />
                <DetailRow
                  label="Query Validation Result"
                  value={message.validationResult ?? "—"}
                />
                {message.dataSource && (
                  <DetailRow label="Data Source" value={message.dataSource} />
                )}
                {message.sql && (
                  <div>
                    <p className="mb-1 text-[11px] uppercase tracking-[0.12em] text-zinc-500">
                      Generated SQL
                    </p>
                    <pre className="overflow-x-auto rounded-lg border border-cyan-500/20 bg-[#020617] p-2 text-[11px] text-sky-200">
                      <code>{message.sql}</code>
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {!isUser && (
          <div className="mt-3 flex flex-wrap items-center gap-2 pt-1">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 gap-1.5 px-2 text-zinc-400 hover:bg-white/5 hover:text-zinc-100"
              onClick={() => void handleCopy()}
              aria-label="Copy answer"
            >
              {copied ? (
                <Check className="h-3.5 w-3.5 text-emerald-400" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
              {copied ? "Copied" : "Copy"}
            </Button>
            {message.error && onRetry && (
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className="h-7 rounded-full border-cyan-400/30 bg-transparent"
                onClick={onRetry}
              >
                <RotateCcw className="h-3.5 w-3.5" />
                Retry
              </Button>
            )}
          </div>
        )}

        {!isUser && followUps.length > 0 && (
          <div className="mt-3 pt-2">
            <p className="mb-2 text-xs text-zinc-400">
              {message.error ? "Try asking" : "Suggested follow-up"}
            </p>
            <div className="flex flex-wrap gap-2">
              {followUps.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => onFollowUp?.(prompt)}
                  className="rounded-full border border-cyan-400/40 bg-transparent px-3.5 py-1.5 text-xs text-cyan-100/90 transition hover:border-cyan-300 hover:bg-cyan-400/10 hover:text-white"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-[0.12em] text-zinc-500">{label}</p>
      <p className="mt-0.5 text-zinc-200">{value}</p>
    </div>
  );
}

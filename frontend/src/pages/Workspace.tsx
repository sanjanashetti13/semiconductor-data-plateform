import { AppShell } from "@/components/AppShell";
import { ChatInput } from "@/components/ChatInput";
import { ChatMessage } from "@/components/ChatMessage";
import { SuggestionChips } from "@/components/SuggestionChips";
import { TypingIndicator } from "@/components/TypingIndicator";
import { Button } from "@/components/ui/button";
import {
  GENERIC_SQL_CHIPS,
  GENERIC_SQL_ERROR_SUGGESTIONS,
  DEVELOPER_MODE_CHANGED_EVENT,
  SQL_SESSION_CHANGED_EVENT,
} from "@/constants/branding";
import {
  chatStorageKeyForSession,
  clearAllChats,
  createId,
  getSqlSessionId,
  loadChat,
  loadDeveloperMode,
  loadSqlSession,
  loadTheme,
  saveChat,
  saveTheme,
  type ThemeMode,
} from "@/lib/storage";
import { ApiError, sendSqlAgentChat } from "@/services/api";
import type { ChatMessage as ChatMessageType } from "@/types";
import { Eraser } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

const CONFIGURE_FIRST_MESSAGE =
  "Please configure a data source first.\n\nOpen **Data Sources**, connect your Azure SQL database, then return here to ask questions in Azure Data Copilot.";

export function Workspace() {
  const initialSession = loadSqlSession();
  const chatKeyRef = useRef(chatStorageKeyForSession(initialSession?.sessionId));
  const [messages, setMessages] = useState<ChatMessageType[]>(() =>
    loadChat(chatKeyRef.current),
  );
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [theme, setTheme] = useState<ThemeMode>(() => loadTheme());
  const [developerMode, setDeveloperMode] = useState(() => loadDeveloperMode());
  const [lastQuestion, setLastQuestion] = useState<string | null>(null);
  const [sqlConnected, setSqlConnected] = useState(() => Boolean(initialSession));
  const [session, setSession] = useState(() => initialSession);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const inFlightRef = useRef(false);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    saveTheme(theme);
  }, [theme]);

  useEffect(() => {
    saveChat(messages, chatKeyRef.current);
  }, [messages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    const syncDev = () => setDeveloperMode(loadDeveloperMode());
    window.addEventListener(DEVELOPER_MODE_CHANGED_EVENT, syncDev);
    window.addEventListener("storage", syncDev);
    return () => {
      window.removeEventListener(DEVELOPER_MODE_CHANGED_EVENT, syncDev);
      window.removeEventListener("storage", syncDev);
    };
  }, []);

  useEffect(() => {
    const sync = () => {
      const next = loadSqlSession();
      const nextKey = chatStorageKeyForSession(next?.sessionId);
      const sessionChanged = nextKey !== chatKeyRef.current;

      setSession(next);
      setSqlConnected(Boolean(next));

      if (sessionChanged) {
        chatKeyRef.current = nextKey;
        setMessages(loadChat(nextKey));
        setLastQuestion(null);
        setInput("");
        inFlightRef.current = false;
        setLoading(false);
      }
    };
    sync();
    window.addEventListener("focus", sync);
    window.addEventListener("storage", sync);
    window.addEventListener(SQL_SESSION_CHANGED_EVENT, sync);
    return () => {
      window.removeEventListener("focus", sync);
      window.removeEventListener("storage", sync);
      window.removeEventListener(SQL_SESSION_CHANGED_EVENT, sync);
    };
  }, []);

  const handleClearChat = useCallback(() => {
    clearAllChats();
    chatKeyRef.current = chatStorageKeyForSession(getSqlSessionId());
    setMessages([]);
    setLastQuestion(null);
    setInput("");
    toast.message("All chats cleared.");
  }, []);

  const ask = useCallback(
    async (question: string) => {
      const trimmed = question.trim();
      if (!trimmed || inFlightRef.current) return;

      const history = messages;
      const sessionId = getSqlSessionId();

      inFlightRef.current = true;
      setLastQuestion(trimmed);
      setMessages((prev) => [
        ...prev,
        {
          id: createId(),
          role: "user",
          content: trimmed,
          timestamp: new Date().toISOString(),
        },
      ]);
      setInput("");
      setLoading(true);

      try {
        if (!sessionId) {
          setMessages((prev) => [
            ...prev,
            {
              id: createId(),
              role: "assistant",
              content: CONFIGURE_FIRST_MESSAGE,
              timestamp: new Date().toISOString(),
              error: true,
            },
          ]);
          toast.message("Configure a data source before chatting.");
          return;
        }

        const response = await sendSqlAgentChat(trimmed, sessionId, history);
        setMessages((prev) => [
          ...prev,
          {
            id: createId(),
            role: "assistant",
            content: response.answer,
            timestamp: new Date().toISOString(),
            tool: response.tool,
            toolLabel: response.tool_label,
            dataSource: response.data_source,
            executionTime: response.execution_time,
            model: response.model,
            followUps: response.follow_ups,
            sql: response.sql,
            category: response.category,
            routerDecision: response.router_decision ?? response.category,
            validationResult: response.validation_result,
            agentsUsed: response.agents_used,
            plannerRationale: response.planner_rationale,
            executionGraph: response.execution_graph,
          },
        ]);
      } catch (error) {
        const detail =
          error instanceof Error
            ? error.message
            : "Unable to retrieve insights.";
        const suggestions =
          error instanceof ApiError && error.suggestions.length > 0
            ? error.suggestions
            : [...GENERIC_SQL_ERROR_SUGGESTIONS];
        toast.error(detail);
        setMessages((prev) => [
          ...prev,
          {
            id: createId(),
            role: "assistant",
            content: `${detail}\n\nHere are relevant questions you can try next.`,
            timestamp: new Date().toISOString(),
            error: true,
            suggestions,
          },
        ]);
      } finally {
        inFlightRef.current = false;
        setLoading(false);
      }
    },
    [messages],
  );

  const empty = messages.length === 0;

  return (
    <AppShell
      theme={theme}
      sqlConnected={sqlConnected}
      onToggleTheme={() => setTheme((prev) => (prev === "dark" ? "light" : "dark"))}
    >
      <main className="relative flex min-h-0 flex-1 flex-col">
        {!empty && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={loading}
            onClick={handleClearChat}
            className="absolute right-3 top-3 z-10 gap-1.5 rounded-full border border-cyan-400/25 bg-[#07111f]/60 text-zinc-300 backdrop-blur-md hover:bg-[#07111f]/80 hover:text-zinc-50"
          >
            <Eraser className="h-3.5 w-3.5" aria-hidden />
            Clear chat
          </Button>
        )}

        <div className="min-h-0 flex-1 overflow-y-auto">
          {empty ? (
            <div className="mx-auto flex min-h-full max-w-3xl flex-col items-center justify-center px-4 py-14 text-center">
              <h1 className="text-3xl font-semibold tracking-tight text-zinc-50 md:text-4xl">
                Welcome to Azure Data Copilot
              </h1>
              {sqlConnected && session ? (
                <>
                  <p className="mt-3 max-w-xl text-sm text-zinc-400">
                    New chat for{" "}
                    <span className="text-zinc-200">{session.database}</span>. Ask
                    natural-language questions about your connected Azure SQL database.
                  </p>
                  <div className="mt-8 w-full">
                    <SuggestionChips
                      disabled={loading}
                      items={GENERIC_SQL_CHIPS}
                      onSelect={(prompt) => void ask(prompt)}
                    />
                  </div>
                </>
              ) : (
                <>
                  <p className="mt-3 max-w-xl text-sm text-zinc-400 md:text-base">
                    Configure a data source first to start chatting.
                  </p>
                  <p className="mt-5 max-w-lg text-sm text-zinc-500">
                    Open{" "}
                    <Link to="/data-sources" className="text-sky-400 hover:underline">
                      Data Sources
                    </Link>
                    , connect Azure SQL, then return here to ask questions.
                  </p>
                </>
              )}
            </div>
          ) : (
            <div className="mx-auto flex w-full flex-col gap-5 py-6 pb-8">
              {messages.map((message, index) => (
                <ChatMessage
                  key={message.id}
                  message={message}
                  developerMode={developerMode}
                  onFollowUp={(prompt) => void ask(prompt)}
                  onRetry={
                    message.error && index === messages.length - 1
                      ? () => {
                          if (lastQuestion) void ask(lastQuestion);
                        }
                      : undefined
                  }
                />
              ))}
              {loading && <TypingIndicator />}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        <div className="px-4 py-4">
          <ChatInput
            value={input}
            loading={loading}
            onChange={setInput}
            onSubmit={() => void ask(input)}
          />
        </div>
      </main>
    </AppShell>
  );
}

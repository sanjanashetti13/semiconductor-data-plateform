import type {
  ChatMessage,
  ChatRequest,
  ChatResponse,
  DatasetInfo,
} from "@/types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  status: number;
  suggestions: string[];

  constructor(message: string, status: number, suggestions: string[] = []) {
    super(message);
    this.status = status;
    this.suggestions = suggestions;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    let detail = "Unable to retrieve manufacturing insights.";
    let suggestions: string[] = [];
    try {
      const body = (await response.json()) as {
        detail?: string | { message?: string; suggestions?: string[] };
      };
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (body.detail && typeof body.detail === "object") {
        detail = body.detail.message ?? detail;
        suggestions = body.detail.suggestions ?? [];
      }
    } catch {
      // keep default
    }
    throw new ApiError(detail, response.status, suggestions);
  }

  return response.json() as Promise<T>;
}

export async function sendChat(
  question: string,
  history: ChatMessage[] = [],
): Promise<ChatResponse> {
  const payload: ChatRequest = {
    question,
    history: history
      .filter((m) => m.role === "user" || m.role === "assistant")
      .slice(-6)
      .map((m) => ({
        role: m.role,
        content: m.content,
      })),
  };

  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getHealth(): Promise<{ status: string }> {
  return request<{ status: string }>("/api/health");
}

export async function getDatasetInfo(): Promise<DatasetInfo> {
  return request<DatasetInfo>("/api/dataset");
}

export interface SqlConnectPayload {
  server: string;
  database: string;
  username: string;
  password: string;
}

export interface SqlConnectResult {
  session_id: string;
  database: string;
  server: string;
  table_count: number;
  schema_preview: string;
}

export interface SqlAgentResponse {
  answer: string;
  sql?: string | null;
  tool: string;
  tool_label: string;
  data_source?: string | null;
  execution_time: number;
  model: string;
  row_count: number;
  follow_ups: string[];
  category?: string | null;
  router_decision?: string | null;
  validation_result?: string | null;
  agents_used?: string[];
  planner_rationale?: string | null;
  execution_graph?: string[];
}

export async function connectSqlDatabase(
  payload: SqlConnectPayload,
): Promise<SqlConnectResult> {
  return request<SqlConnectResult>("/api/sql-agent/connect", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function sendSqlAgentChat(
  question: string,
  sessionId: string,
  history: ChatMessage[] = [],
): Promise<SqlAgentResponse> {
  return request<SqlAgentResponse>("/api/sql-agent/chat", {
    method: "POST",
    body: JSON.stringify({
      question,
      session_id: sessionId,
      history: history
        .filter((m) => m.role === "user" || m.role === "assistant")
        .slice(-6)
        .map((m) => ({ role: m.role, content: m.content })),
    }),
  });
}

export async function disconnectSqlSession(sessionId: string): Promise<void> {
  await request(`/api/sql-agent/session/${sessionId}`, { method: "DELETE" });
}

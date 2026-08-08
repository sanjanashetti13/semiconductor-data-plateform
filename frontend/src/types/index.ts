export type MessageRole = "user" | "assistant";
export type ConfidenceLevel = "High" | "Medium" | "Low";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  tool?: string | null;
  toolLabel?: string | null;
  dataSource?: string | null;
  responseMode?: string | null;
  executionTime?: number;
  model?: string;
  confidence?: ConfidenceLevel;
  followUps?: string[];
  sql?: string | null;
  category?: string | null;
  routerDecision?: string | null;
  validationResult?: string | null;
  error?: boolean;
  suggestions?: string[];
}

export interface HistoryMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  question: string;
  history?: HistoryMessage[];
}

export interface ChatResponse {
  answer: string;
  tool?: string | null;
  tool_label?: string | null;
  data_source?: string | null;
  response_mode?: string | null;
  execution_time: number;
  model: string;
  confidence: ConfidenceLevel;
  follow_ups: string[];
  sql?: string | null;
}

export interface DatasetInfo {
  name: string;
  row_count: number | null;
  sensor_count: number | null;
  database: string;
  table: string;
}

export interface AzureSqlConfig {
  server: string;
  database: string;
  username: string;
  password: string;
}

export interface SuggestionChip {
  label: string;
  prompt: string;
}

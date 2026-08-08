import type { AzureSqlConfig, ChatMessage } from "@/types";
import {
  AZURE_SQL_STORAGE_KEY,
  CHAT_STORAGE_KEY,
  DEVELOPER_MODE_CHANGED_EVENT,
  DEVELOPER_MODE_STORAGE_KEY,
  POWER_BI_STORAGE_KEY,
  SQL_NEEDS_CONFIG_KEY,
  SQL_SESSION_CHANGED_EVENT,
  SQL_SESSION_KEY,
  SQL_SESSION_META_KEY,
  THEME_STORAGE_KEY,
} from "@/constants/branding";

function notifySqlSessionChanged(): void {
  window.dispatchEvent(new Event(SQL_SESSION_CHANGED_EVENT));
}

export function createId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

/** One chat thread per SQL connection session — never shared across connections. */
export function chatStorageKeyForSession(sessionId: string | null | undefined): string {
  return sessionId
    ? `${CHAT_STORAGE_KEY}:session:${sessionId}`
    : `${CHAT_STORAGE_KEY}:disconnected`;
}

export function loadChat(key = CHAT_STORAGE_KEY): ChatMessage[] {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ChatMessage[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveChat(messages: ChatMessage[], key = CHAT_STORAGE_KEY): void {
  localStorage.setItem(key, JSON.stringify(messages));
}

export function clearChat(key = CHAT_STORAGE_KEY): void {
  localStorage.removeItem(key);
}

/** Remove every workspace chat thread (all connections). */
export function clearAllChats(): void {
  const keys: string[] = [];
  for (let i = 0; i < localStorage.length; i += 1) {
    const key = localStorage.key(i);
    if (key && key.startsWith(CHAT_STORAGE_KEY)) keys.push(key);
  }
  for (const key of keys) localStorage.removeItem(key);
}

export function loadPowerBiUrl(): string {
  return (
    localStorage.getItem(POWER_BI_STORAGE_KEY) ??
    import.meta.env.VITE_POWERBI_URL ??
    ""
  );
}

export function savePowerBiUrl(url: string): void {
  localStorage.setItem(POWER_BI_STORAGE_KEY, url.trim());
}

export function loadAzureSqlConfig(): AzureSqlConfig {
  try {
    const raw = localStorage.getItem(AZURE_SQL_STORAGE_KEY);
    if (!raw) {
      return { server: "", database: "", username: "", password: "" };
    }
    const parsed = JSON.parse(raw) as AzureSqlConfig;
    return {
      server: parsed.server ?? "",
      database: parsed.database ?? "",
      username: parsed.username ?? "",
      password: "",
    };
  } catch {
    return { server: "", database: "", username: "", password: "" };
  }
}

export function saveAzureSqlConfig(config: AzureSqlConfig): void {
  localStorage.setItem(
    AZURE_SQL_STORAGE_KEY,
    JSON.stringify({
      server: config.server,
      database: config.database,
      username: config.username,
      password: "",
    }),
  );
}

export interface SqlSessionMeta {
  sessionId: string;
  server: string;
  database: string;
  tableCount: number;
  viewCount: number;
  schemaLoaded: boolean;
}

export function loadSqlSession(): SqlSessionMeta | null {
  try {
    const raw = sessionStorage.getItem(SQL_SESSION_META_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as SqlSessionMeta;
  } catch {
    return null;
  }
}

export function saveSqlSession(meta: SqlSessionMeta): void {
  sessionStorage.setItem(SQL_SESSION_KEY, meta.sessionId);
  sessionStorage.setItem(SQL_SESSION_META_KEY, JSON.stringify(meta));
  sessionStorage.removeItem(SQL_NEEDS_CONFIG_KEY);
  notifySqlSessionChanged();
}

export function clearSqlSession(): void {
  sessionStorage.removeItem(SQL_SESSION_KEY);
  sessionStorage.removeItem(SQL_SESSION_META_KEY);
  sessionStorage.setItem(SQL_NEEDS_CONFIG_KEY, "1");
  notifySqlSessionChanged();
}

export function getSqlSessionId(): string | null {
  return sessionStorage.getItem(SQL_SESSION_KEY);
}

/** True after Disconnect until the user connects a data source again. */
export function needsDataSourceConfig(): boolean {
  return (
    sessionStorage.getItem(SQL_NEEDS_CONFIG_KEY) === "1" &&
    !sessionStorage.getItem(SQL_SESSION_KEY)
  );
}

export type ThemeMode = "dark" | "light";

export function loadTheme(): ThemeMode {
  const stored = localStorage.getItem(THEME_STORAGE_KEY);
  if (stored === "light" || stored === "dark") return stored;
  return "dark";
}

export function saveTheme(theme: ThemeMode): void {
  localStorage.setItem(THEME_STORAGE_KEY, theme);
}

/** Developer Mode is OFF by default (Copilot-style business answers). */
export function loadDeveloperMode(): boolean {
  return localStorage.getItem(DEVELOPER_MODE_STORAGE_KEY) === "1";
}

export function saveDeveloperMode(enabled: boolean): void {
  localStorage.setItem(DEVELOPER_MODE_STORAGE_KEY, enabled ? "1" : "0");
  window.dispatchEvent(new Event(DEVELOPER_MODE_CHANGED_EVENT));
}

export function clearPowerBiUrl(): void {
  localStorage.removeItem(POWER_BI_STORAGE_KEY);
}

/** Clear SQL session and chats on disconnect. */
export function clearWorkspaceOnDisconnect(options?: { clearPowerBi?: boolean }): void {
  const sessionId = getSqlSessionId();
  if (sessionId) {
    clearChat(chatStorageKeyForSession(sessionId));
  }
  clearAllChats();
  clearSqlSession();
  if (options?.clearPowerBi) {
    clearPowerBiUrl();
  }
}

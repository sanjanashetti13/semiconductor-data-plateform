import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  chatStorageKeyForSession,
  clearChat,
  clearWorkspaceOnDisconnect,
  loadAzureSqlConfig,
  loadSqlSession,
  loadTheme,
  saveAzureSqlConfig,
  saveSqlSession,
  saveTheme,
  type ThemeMode,
} from "@/lib/storage";
import { ApiError, connectSqlDatabase, disconnectSqlSession } from "@/services/api";
import type { AzureSqlConfig } from "@/types";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

function parseSchemaCounts(preview: string): { tables: number; views: number } {
  const lines = preview.split("\n");
  let tables = 0;
  let views = 0;
  for (const line of lines) {
    const trimmed = line.trim();
    if (/^[\w.]+\s+\(TABLE\)/.test(trimmed)) {
      tables += 1;
      continue;
    }
    if (/^[\w.]+\s+\(VIEW\)/.test(trimmed)) {
      views += 1;
      continue;
    }
    if (!trimmed.startsWith("## ")) continue;
    if (trimmed.toUpperCase().includes("(VIEW)")) views += 1;
    else tables += 1;
  }
  return { tables, views };
}

export function DataSourcesPage() {
  const navigate = useNavigate();
  const [theme, setTheme] = useState<ThemeMode>(() => loadTheme());
  const [form, setForm] = useState<AzureSqlConfig>(() => loadAzureSqlConfig());
  const [busy, setBusy] = useState<"test" | "connect" | null>(null);
  const [preview, setPreview] = useState("");
  const [session, setSession] = useState(() => loadSqlSession());

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    saveTheme(theme);
  }, [theme]);

  function update<K extends keyof AzureSqlConfig>(key: K, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function validateForm(): boolean {
    if (!form.server.trim() || !form.database.trim() || !form.username.trim() || !form.password) {
      toast.error("Fill in Server, Database, Username, and Password.");
      return false;
    }
    return true;
  }

  async function runConnect(thenOpenCopilot: boolean) {
    if (!validateForm()) return;

    setBusy(thenOpenCopilot ? "connect" : "test");
    try {
      const previous = loadSqlSession();
      if (previous) {
        try {
          await disconnectSqlSession(previous.sessionId);
        } catch {
          // continue
        }
        clearChat(chatStorageKeyForSession(previous.sessionId));
      }

      const result = await connectSqlDatabase({
        server: form.server.trim(),
        database: form.database.trim(),
        username: form.username.trim(),
        password: form.password,
      });
      const counts = parseSchemaCounts(result.schema_preview);
      const meta = {
        sessionId: result.session_id,
        server: result.server,
        database: result.database,
        tableCount: counts.tables || result.table_count,
        viewCount: counts.views,
        schemaLoaded: true,
      };

      clearChat(chatStorageKeyForSession(meta.sessionId));
      saveAzureSqlConfig(form);
      saveSqlSession(meta);
      setSession(meta);
      setPreview(result.schema_preview);

      if (thenOpenCopilot) {
        const semi =
          /fact_sensor_readings/i.test(result.schema_preview) ||
          /vw_manufacturing_summary/i.test(result.schema_preview);
        toast.success(
          semi
            ? `Connected · Semiconductor Mode · ${result.database}`
            : `Connected · Generic SQL Mode · ${result.database}`,
        );
        navigate("/copilot");
      } else {
        toast.success(
          `Connection OK · ${counts.tables || result.table_count} tables, ${counts.views} views`,
        );
      }
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : "Unable to connect to Azure SQL.";
      toast.error(message);
    } finally {
      setBusy(null);
    }
  }

  function handleSave() {
    saveAzureSqlConfig(form);
    toast.success("Connection details saved for this browser (password not stored).");
  }

  async function handleDisconnect() {
    const active = loadSqlSession();
    if (active) {
      try {
        await disconnectSqlSession(active.sessionId);
      } catch {
        // clear locally anyway
      }
    }
    clearWorkspaceOnDisconnect();
    setForm((prev) => ({ ...prev, password: "" }));
    setSession(null);
    setPreview("");
    toast.message("Disconnected. Configure Azure SQL before using AI Copilot.");
  }

  return (
    <AppShell
      theme={theme}
      sqlConnected={Boolean(session)}
      onToggleTheme={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
    >
      <div className="mx-auto w-full max-w-2xl px-4 py-10">
        <h1 className="text-2xl font-semibold text-zinc-50">Database Connection</h1>
        <p className="mt-2 text-sm text-zinc-400">
          Connect any Azure SQL database. Credentials are held in server memory for this
          session only and are removed on Disconnect. Semiconductor warehouses are detected
          automatically for domain-aware analytics.
        </p>

        <div className="mt-6 grid gap-3 rounded-2xl border border-cyan-400/25 bg-[#07111f]/70 p-5 shadow-[0_0_28px_rgba(34,211,238,0.08)] backdrop-blur-md">
          {(
            [
              ["server", "Server", "your-server.database.windows.net", "off"],
              ["database", "Database", "my_database", "off"],
              ["username", "Username", "sqladmin", "username"],
              ["password", "Password", "••••••••", "current-password"],
            ] as const
          ).map(([key, label, placeholder, autoComplete]) => (
            <div key={key}>
              <label className="mb-1 block text-xs text-zinc-400" htmlFor={key}>
                {label}
              </label>
              <Input
                id={key}
                type={key === "password" ? "password" : "text"}
                value={form[key]}
                onChange={(e) => update(key, e.target.value)}
                placeholder={placeholder}
                autoComplete={autoComplete}
                disabled={Boolean(busy)}
              />
            </div>
          ))}

          <div className="mt-2 flex flex-wrap gap-2">
            <Button
              type="button"
              variant="secondary"
              disabled={Boolean(busy)}
              onClick={() => void runConnect(false)}
            >
              {busy === "test" ? "Testing…" : "Test Connection"}
            </Button>
            <Button
              type="button"
              variant="accent"
              disabled={Boolean(busy)}
              onClick={() => void runConnect(true)}
            >
              {busy === "connect" ? "Connecting…" : "Connect"}
            </Button>
            <Button type="button" variant="secondary" disabled={Boolean(busy)} onClick={handleSave}>
              Save Connection
            </Button>
            <Button
              type="button"
              variant="ghost"
              disabled={!session || Boolean(busy)}
              onClick={() => void handleDisconnect()}
            >
              Disconnect
            </Button>
          </div>
        </div>

        <div className="mt-6 rounded-2xl border border-cyan-400/25 bg-[#07111f]/65 p-5 shadow-[0_0_28px_rgba(34,211,238,0.08)] backdrop-blur-md">
          <h2 className="text-sm font-medium text-zinc-200">Connection Status</h2>
          {session ? (
            <dl className="mt-3 grid gap-2 text-sm text-zinc-400 sm:grid-cols-2">
              <div>
                <dt className="text-xs text-zinc-500">Operating Mode</dt>
                <dd className="text-zinc-300">
                  {/fact_sensor_readings|vw_manufacturing_summary/i.test(preview)
                    ? "Semiconductor Mode"
                    : "Generic SQL Mode"}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-zinc-500">Connection Status</dt>
                <dd className="text-emerald-300">Connected</dd>
              </div>
              <div>
                <dt className="text-xs text-zinc-500">Database Name</dt>
                <dd className="text-zinc-200">{session.database}</dd>
              </div>
              <div>
                <dt className="text-xs text-zinc-500">Server</dt>
                <dd className="text-zinc-200">{session.server}</dd>
              </div>
              <div>
                <dt className="text-xs text-zinc-500">Detected Tables</dt>
                <dd className="text-zinc-200">{session.tableCount}</dd>
              </div>
              <div>
                <dt className="text-xs text-zinc-500">Detected Views</dt>
                <dd className="text-zinc-200">{session.viewCount}</dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-xs text-zinc-500">Schema Loaded</dt>
                <dd className="text-zinc-200">
                  {session.schemaLoaded
                    ? "Yes — INFORMATION_SCHEMA inspected (compact)"
                    : "No"}
                </dd>
              </div>
            </dl>
          ) : (
            <dl className="mt-3 grid gap-2 text-sm text-zinc-400">
              <div>
                <dt className="text-xs text-zinc-500">Operating Mode</dt>
                <dd className="text-amber-300">Not connected</dd>
              </div>
              <div>
                <dt className="text-xs text-zinc-500">Connection Status</dt>
                <dd>Not connected — configure Azure SQL before using AI Copilot.</dd>
              </div>
            </dl>
          )}
        </div>

        {preview && (
          <div className="mt-6">
            <h2 className="mb-2 text-sm font-medium text-zinc-200">
              Load Database Schema
            </h2>
            <pre className="max-h-72 overflow-auto rounded-xl border border-zinc-800 bg-zinc-950 p-4 text-xs text-zinc-500">
              {preview}
            </pre>
          </div>
        )}
      </div>
    </AppShell>
  );
}

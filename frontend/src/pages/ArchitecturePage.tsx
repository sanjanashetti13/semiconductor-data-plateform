import { AppShell } from "@/components/AppShell";
import { loadSqlSession, loadTheme, saveTheme, type ThemeMode } from "@/lib/storage";
import { useEffect, useState } from "react";

const FLOW = [
  "User",
  "React Frontend",
  "FastAPI",
  "AI Router",
  "Semiconductor Database  OR  Connected Azure SQL",
  "Groq LLM",
  "Natural Language Response",
];

export function ArchitecturePage() {
  const [theme, setTheme] = useState<ThemeMode>(() => loadTheme());
  const sqlConnected = Boolean(loadSqlSession());

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    saveTheme(theme);
  }, [theme]);

  return (
    <AppShell
      theme={theme}
      sqlConnected={sqlConnected}
      onToggleTheme={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
    >
      <div className="mx-auto max-w-2xl px-4 py-10">
        <h1 className="text-2xl font-semibold text-zinc-50">Platform Architecture</h1>
        <p className="mt-2 text-sm text-zinc-400">
          Enterprise AI analytics platform with dual operating modes over Azure SQL.
        </p>

        <div className="mt-8 space-y-0 rounded-2xl border border-cyan-400/25 bg-[#07111f]/70 p-6 shadow-[0_0_28px_rgba(34,211,238,0.08)] backdrop-blur-md">
          {FLOW.map((label, index) => (
            <div key={label} className="flex flex-col items-center">
              <div className="w-full rounded-xl border border-cyan-400/20 bg-[#020617]/70 px-4 py-3 text-center text-sm text-zinc-100">
                {label}
              </div>
              {index < FLOW.length - 1 && (
                <div className="py-1 text-zinc-600">↓</div>
              )}
            </div>
          ))}
        </div>

        <div className="mt-6 space-y-3 text-sm leading-relaxed text-zinc-400">
          <p>
            Users interact through a React frontend that talks to FastAPI. An AI Router
            directs each question to either the semiconductor manufacturing tools or a
            schema-aware SQL path for a user-connected Azure SQL database.
          </p>
          <p>
            In Semiconductor Mode, curated warehouse data powers manufacturing analytics. In
            Generic SQL Mode, the platform inspects INFORMATION_SCHEMA, generates safe
            SELECT queries, and returns natural-language explanations via Groq.
          </p>
          <p>
            Azure Databricks (Bronze → Silver → Gold) and Power BI remain part of the
            platform data/BI plane, while the chat experience stays focused on natural
            language analytics.
          </p>
        </div>
      </div>
    </AppShell>
  );
}

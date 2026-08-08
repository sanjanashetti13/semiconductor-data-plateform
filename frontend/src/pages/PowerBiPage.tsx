import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import {
  loadPowerBiUrl,
  loadSqlSession,
  loadTheme,
  savePowerBiUrl,
  saveTheme,
  type ThemeMode,
} from "@/lib/storage";
import { ExternalLink } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

export function PowerBiPage() {
  const [theme, setTheme] = useState<ThemeMode>(() => loadTheme());
  const [url, setUrl] = useState(() => loadPowerBiUrl());
  const [configureOpen, setConfigureOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const sqlConnected = Boolean(loadSqlSession());

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    saveTheme(theme);
  }, [theme]);

  function openDashboard() {
    const configured = loadPowerBiUrl();
    if (!configured) {
      setDraft("");
      setError("");
      setConfigureOpen(true);
      return;
    }
    window.open(configured, "_blank", "noopener,noreferrer");
  }

  function saveConfig() {
    const trimmed = draft.trim();
    if (!trimmed) {
      setError("Paste a Power BI dashboard or embed URL.");
      return;
    }
    try {
      new URL(trimmed);
    } catch {
      setError("Enter a valid URL (https://...).");
      return;
    }
    savePowerBiUrl(trimmed);
    setUrl(trimmed);
    setConfigureOpen(false);
    toast.success("Dashboard URL saved locally.");
  }

  return (
    <AppShell
      theme={theme}
      sqlConnected={sqlConnected}
      onToggleTheme={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
    >
      <div className="mx-auto flex max-w-xl flex-col items-center px-4 py-16 text-center">
        <h1 className="text-2xl font-semibold text-zinc-50">Power BI Dashboard</h1>
        <p className="mt-3 text-sm text-zinc-400">
          Executive dashboards stay in Power BI. This platform only opens your published
          report — it does not recreate visuals.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-2">
          <Button type="button" variant="accent" onClick={openDashboard}>
            Open Dashboard
            <ExternalLink className="h-3.5 w-3.5" />
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              setDraft(url);
              setError("");
              setConfigureOpen(true);
            }}
          >
            Configure Dashboard
          </Button>
        </div>
        {url ? (
          <p className="mt-4 max-w-md truncate text-xs text-zinc-500" title={url}>
            Configured: {url}
          </p>
        ) : (
          <p className="mt-4 text-xs text-zinc-500">No dashboard URL configured yet.</p>
        )}
      </div>

      <Modal
        open={configureOpen}
        onClose={() => setConfigureOpen(false)}
        title="Configure Dashboard"
      >
        <p className="mb-3 text-sm text-zinc-400">
          Paste a Power BI Dashboard URL or Embed URL. Stored locally in this browser only.
        </p>
        <Input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="https://app.powerbi.com/..."
          autoFocus
        />
        {error && <p className="mt-2 text-xs text-rose-400">{error}</p>}
        <div className="mt-4 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={() => setConfigureOpen(false)}>
            Cancel
          </Button>
          <Button type="button" variant="accent" onClick={saveConfig}>
            Save
          </Button>
        </div>
      </Modal>
    </AppShell>
  );
}

import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import {
  canEmbedPowerBiUrl,
  classifyPowerBiUrl,
  getOpenablePowerBiUrl,
  truncateUrl,
  validatePowerBiUrl,
} from "@/lib/powerBi";
import {
  loadPowerBiUrl,
  loadSqlSession,
  loadTheme,
  savePowerBiUrl,
  saveTheme,
  type ThemeMode,
} from "@/lib/storage";
import { ExternalLink, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

export function PowerBiPage() {
  const [theme, setTheme] = useState<ThemeMode>(() => loadTheme());
  const [url, setUrl] = useState(() => loadPowerBiUrl());
  const [configureOpen, setConfigureOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [iframeError, setIframeError] = useState(false);
  const sqlConnected = Boolean(loadSqlSession());

  const kind = useMemo(() => classifyPowerBiUrl(url), [url]);
  const openable = useMemo(() => (url ? getOpenablePowerBiUrl(url) : ""), [url]);
  const showEmbed = Boolean(url && canEmbedPowerBiUrl(url) && !iframeError);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    saveTheme(theme);
  }, [theme]);

  useEffect(() => {
    setIframeError(false);
  }, [url]);

  function openDashboard() {
    const configured = loadPowerBiUrl().trim();
    if (!configured) {
      setDraft("");
      setError("");
      setConfigureOpen(true);
      toast.message("Configure a Power BI report URL first.");
      return;
    }
    const validation = validatePowerBiUrl(configured);
    if (validation) {
      setDraft(configured);
      setError(validation);
      setConfigureOpen(true);
      toast.error(validation);
      return;
    }
    const target = getOpenablePowerBiUrl(configured);
    const win = window.open(target, "_blank", "noopener,noreferrer");
    if (!win) {
      toast.error("Popup blocked. Allow popups for this site, or use the embedded view below.");
      return;
    }
    if (classifyPowerBiUrl(configured) === "embed") {
      toast.message("Opened embed link. Sign in to Microsoft if Power BI asks.");
    }
  }

  function saveConfig() {
    const trimmed = draft.trim();
    const validation = validatePowerBiUrl(trimmed);
    if (validation) {
      setError(validation);
      return;
    }
    const normalized = getOpenablePowerBiUrl(trimmed);
    savePowerBiUrl(normalized);
    setUrl(normalized);
    setConfigureOpen(false);
    setIframeError(false);
    toast.success("Dashboard URL saved in this browser.");
  }

  function clearConfig() {
    savePowerBiUrl("");
    setUrl("");
    setDraft("");
    setIframeError(false);
    toast.success("Dashboard URL cleared.");
  }

  return (
    <AppShell
      theme={theme}
      sqlConnected={sqlConnected}
      onToggleTheme={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
    >
      <div className="mx-auto flex w-full max-w-5xl flex-col px-4 py-10">
        <div className="mx-auto max-w-xl text-center">
          <h1 className="text-2xl font-semibold text-zinc-50">Power BI Dashboard</h1>
          <p className="mt-3 text-sm text-zinc-400">
            Executive dashboards stay in Power BI. This page opens or embeds your published
            report — it does not recreate visuals or store tokens.
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
            {url ? (
              <Button type="button" variant="ghost" onClick={clearConfig}>
                <Trash2 className="h-3.5 w-3.5" />
                Clear
              </Button>
            ) : null}
          </div>
          {url ? (
            <p className="mt-4 text-xs text-zinc-500" title={url}>
              Configured ({kind}): {truncateUrl(url, 72)}
            </p>
          ) : (
            <p className="mt-4 text-xs text-zinc-500">No dashboard URL configured yet.</p>
          )}
        </div>

        {showEmbed ? (
          <div className="mt-8 overflow-hidden rounded-2xl border border-cyan-500/25 bg-[#020617]/80 shadow-[0_0_40px_rgba(34,211,238,0.08)]">
            <div className="flex items-center justify-between gap-2 border-b border-cyan-500/15 px-3 py-2">
              <p className="text-xs text-zinc-400">
                Embedded preview — sign in to Microsoft if the report asks for access.
              </p>
              <button
                type="button"
                className="text-xs text-cyan-300/90 hover:text-cyan-200"
                onClick={openDashboard}
              >
                Open in new tab
              </button>
            </div>
            <iframe
              title="Power BI report"
              src={openable}
              className="h-[min(70vh,720px)] w-full bg-[#020617]"
              allow="fullscreen"
              referrerPolicy="strict-origin-when-cross-origin"
              onError={() => setIframeError(true)}
            />
          </div>
        ) : url ? (
          <div className="mt-8 rounded-2xl border border-amber-500/30 bg-amber-500/5 px-4 py-6 text-center text-sm text-zinc-300">
            <p>
              This URL could not be embedded here. Use <strong>Open Dashboard</strong> to view
              it in Power BI (you must be signed in to your Microsoft account).
            </p>
            {iframeError ? (
              <p className="mt-2 text-xs text-zinc-500">
                Embeds are blocked for some org reports. Share links or &quot;Publish to
                web&quot; URLs embed more reliably.
              </p>
            ) : null}
          </div>
        ) : (
          <div className="mt-8 rounded-2xl border border-cyan-500/20 bg-[#020617]/50 px-4 py-6 text-left text-sm text-zinc-400">
            <p className="font-medium text-zinc-300">How to get a working URL</p>
            <ol className="mt-2 list-decimal space-y-1.5 pl-5">
              <li>Open your report in Power BI Service (app.powerbi.com).</li>
              <li>
                Use <strong>Share → Copy link</strong>, or{" "}
                <strong>File → Embed report → Website or portal</strong>.
              </li>
              <li>Paste that https://app.powerbi.com/… link via Configure Dashboard.</li>
            </ol>
          </div>
        )}
      </div>

      <Modal
        open={configureOpen}
        onClose={() => setConfigureOpen(false)}
        title="Configure Dashboard"
      >
        <p className="mb-3 text-sm text-zinc-400">
          Paste a Power BI share link or embed URL. Stored only in this browser — never sent to
          our API.
        </p>
        <Input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="https://app.powerbi.com/groups/.../reports/..."
          autoFocus
        />
        {error ? <p className="mt-2 text-xs text-rose-400">{error}</p> : null}
        <p className="mt-3 text-[11px] leading-relaxed text-zinc-500">
          Prefer a report share link. Embed URLs (reportEmbed) work best when you are already
          signed into Power BI in this browser.
        </p>
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

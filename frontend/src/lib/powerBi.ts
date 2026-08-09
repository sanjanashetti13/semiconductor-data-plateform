/** Power BI URL helpers — browser-local config only (no tokens/secrets). */

const POWER_BI_HOSTS = [
  "app.powerbi.com",
  "powerbi.com",
  "msit.powerbi.com",
  "analysis.windows.net",
];

const PLACEHOLDER_RE =
  /aaaaaaaa|00000000-0000|your-report|example\.com|localhost|reportId=$/i;

export type PowerBiUrlKind = "app" | "embed" | "view" | "other" | "invalid";

export function classifyPowerBiUrl(raw: string): PowerBiUrlKind {
  const trimmed = (raw || "").trim();
  if (!trimmed) return "invalid";
  let parsed: URL;
  try {
    parsed = new URL(trimmed);
  } catch {
    return "invalid";
  }
  if (parsed.protocol !== "https:" && parsed.protocol !== "http:") {
    return "invalid";
  }
  const host = parsed.hostname.toLowerCase();
  const isPowerBi = POWER_BI_HOSTS.some(
    (h) => host === h || host.endsWith(`.${h}`),
  );
  if (!isPowerBi) return "invalid";

  const path = parsed.pathname.toLowerCase();
  const search = parsed.search.toLowerCase();
  if (path.includes("reportembed") || search.includes("reportembed")) {
    return "embed";
  }
  if (path.includes("/view") || search.startsWith("?r=")) {
    return "view";
  }
  if (path.includes("/reports/") || path.includes("/groups/")) {
    return "app";
  }
  return "other";
}

export function validatePowerBiUrl(raw: string): string | null {
  const trimmed = (raw || "").trim();
  if (!trimmed) return "Paste a Power BI report, share, or embed URL.";
  let parsed: URL;
  try {
    parsed = new URL(trimmed);
  } catch {
    return "Enter a valid URL starting with https://";
  }
  if (parsed.protocol !== "https:") {
    return "Use an https:// Power BI URL.";
  }
  const kind = classifyPowerBiUrl(trimmed);
  if (kind === "invalid") {
    return "URL must be from app.powerbi.com (or another Microsoft Power BI host).";
  }
  if (PLACEHOLDER_RE.test(trimmed)) {
    return "That looks like a placeholder URL. Paste your real report link from Power BI.";
  }
  if (kind === "other" && parsed.pathname === "/") {
    return "Paste a specific report link, not the Power BI home page.";
  }
  return null;
}

/** Prefer a URL that works in a new browser tab when possible. */
export function getOpenablePowerBiUrl(raw: string): string {
  const trimmed = (raw || "").trim();
  const kind = classifyPowerBiUrl(trimmed);
  if (kind === "invalid") return trimmed;

  try {
    const parsed = new URL(trimmed);
    // Embed URLs often need iframe context; still return them for open attempts.
    // Ensure autoAuth for org reports when missing (helps signed-in users).
    if (kind === "embed" && !parsed.searchParams.has("autoAuth")) {
      parsed.searchParams.set("autoAuth", "true");
      return parsed.toString();
    }
    return parsed.toString();
  } catch {
    return trimmed;
  }
}

export function canEmbedPowerBiUrl(raw: string): boolean {
  const kind = classifyPowerBiUrl(raw);
  return kind === "embed" || kind === "view" || kind === "app";
}

export function truncateUrl(url: string, max = 64): string {
  const t = url.trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max - 1)}…`;
}

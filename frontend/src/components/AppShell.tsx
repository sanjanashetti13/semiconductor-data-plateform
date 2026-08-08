import type { ReactNode } from "react";
import { SettingsModal } from "@/components/modals/SettingsModal";
import { Button } from "@/components/ui/button";
import { APP_NAME, APP_TAGLINE } from "@/constants/branding";
import type { ThemeMode } from "@/lib/storage";
import {
  Database,
  LayoutDashboard,
  MessageSquare,
  Moon,
  Settings,
  Sun,
  Workflow,
} from "lucide-react";
import { useState } from "react";
import { NavLink } from "react-router-dom";

interface AppShellProps {
  theme: ThemeMode;
  sqlConnected?: boolean;
  onToggleTheme: () => void;
  children: ReactNode;
}

const NAV_ITEMS = [
  { to: "/copilot", label: "AI Copilot", icon: MessageSquare },
  { to: "/data-sources", label: "Data Sources", icon: Database },
  { to: "/power-bi", label: "Power BI", icon: LayoutDashboard },
  { to: "/architecture", label: "Platform Architecture", icon: Workflow },
] as const;

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-3 rounded-2xl px-3.5 py-2.5 text-sm font-medium transition ${
    isActive
      ? "bg-zinc-600 text-white shadow-[0_0_24px_rgba(113,113,122,0.35)]"
      : "text-zinc-300 hover:bg-white/5 hover:text-white"
  }`;

function BrandMark() {
  return (
    <div className="relative flex h-14 w-14 shrink-0 items-center justify-center" aria-hidden>
      <svg
        viewBox="0 0 64 64"
          className="h-14 w-14 drop-shadow-[0_0_16px_rgba(161,161,170,0.55)]"
      >
        <defs>
          <linearGradient id="brand-cloud-grad" x1="8%" y1="10%" x2="92%" y2="90%">
            <stop offset="0%" stopColor="#e4e4e7" />
            <stop offset="40%" stopColor="#a1a1aa" />
            <stop offset="100%" stopColor="#71717a" />
          </linearGradient>
          <filter id="brand-cloud-glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="2.2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <path
          filter="url(#brand-cloud-glow)"
          fill="url(#brand-cloud-grad)"
          d="M46.5 42.5H18.8c-6.1 0-11-4.7-11-10.5 0-5.1 3.6-9.4 8.5-10.5C18 15.8 23.7 12 30.4 12c6.2 0 11.5 3.3 14.1 8.2 1.1-.3 2.2-.5 3.4-.5 6.2 0 11.1 4.7 11.1 10.5 0 5.8-5 10.3-12.5 12.3z"
        />
        <path
          fill="none"
          stroke="rgba(255,255,255,0.45)"
          strokeWidth="1.4"
          d="M46.5 42.5H18.8c-6.1 0-11-4.7-11-10.5 0-5.1 3.6-9.4 8.5-10.5C18 15.8 23.7 12 30.4 12c6.2 0 11.5 3.3 14.1 8.2 1.1-.3 2.2-.5 3.4-.5 6.2 0 11.1 4.7 11.1 10.5 0 5.8-5 10.3-12.5 12.3z"
        />
      </svg>
    </div>
  );
}

export function AppShell({
  theme,
  sqlConnected = false,
  onToggleTheme,
  children,
}: AppShellProps) {
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <div className="relative flex min-h-screen text-zinc-100">
      <div
        className="pointer-events-none fixed inset-0 -z-20 bg-cover bg-center bg-no-repeat"
        style={{ backgroundImage: "url(/azure-skyline.png)" }}
        aria-hidden
      />
      <div
        className="pointer-events-none fixed inset-0 -z-10 bg-gradient-to-b from-[#020617]/35 via-[#020617]/40 to-[#020617]/65"
        aria-hidden
      />

      <aside className="sticky top-0 z-40 flex h-screen w-[15.5rem] shrink-0 flex-col gap-3 p-3">
        <div className="flex items-start gap-3 rounded-2xl border border-cyan-400/25 bg-[#07111f]/75 px-3.5 py-3.5 shadow-[0_0_28px_rgba(34,211,238,0.08)] backdrop-blur-xl">
          <BrandMark />
          <div className="min-w-0 pt-0.5">
            <p className="text-[15px] font-semibold leading-tight tracking-tight text-white">
              {APP_NAME}
            </p>
            <p className="mt-1 text-[11px] leading-snug text-zinc-400">
              {APP_TAGLINE}
            </p>
            <p
              className={`mt-2 text-[10px] font-medium ${
                sqlConnected ? "text-zinc-300" : "text-sky-300/80"
              }`}
            >
              {sqlConnected ? "Connected · SQL Mode" : "Not connected"}
            </p>
          </div>
        </div>

        <div className="flex min-h-0 flex-1 flex-col rounded-[1.75rem] border border-cyan-400/25 bg-[#07111f]/70 shadow-[0_0_40px_rgba(34,211,238,0.08)] backdrop-blur-xl">
          <nav className="flex flex-1 flex-col gap-1.5 px-3 pt-3" aria-label="Primary">
            {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
              <NavLink key={to} to={to} className={linkClass}>
                <Icon className="h-4 w-4 shrink-0 opacity-90" aria-hidden />
                <span>{label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-1 px-3 pb-4 pt-2">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => setSettingsOpen(true)}
              aria-label="Open settings"
              className="rounded-full text-zinc-400 hover:bg-white/5 hover:text-white"
            >
              <Settings className="h-4 w-4" />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={onToggleTheme}
              aria-label={
                theme === "dark" ? "Switch to light mode" : "Switch to dark mode"
              }
              className="rounded-full text-zinc-400 hover:bg-white/5 hover:text-white"
            >
              {theme === "dark" ? (
                <Sun className="h-4 w-4" />
              ) : (
                <Moon className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </aside>

      <div className="relative z-0 flex min-h-0 min-w-0 flex-1 flex-col">
        {children}
      </div>

      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}

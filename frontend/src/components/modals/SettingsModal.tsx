import { Modal } from "@/components/ui/modal";
import {
  loadDeveloperMode,
  saveDeveloperMode,
} from "@/lib/storage";
import { useEffect, useState } from "react";

interface SettingsModalProps {
  open: boolean;
  onClose: () => void;
}

export function SettingsModal({ open, onClose }: SettingsModalProps) {
  const [developerMode, setDeveloperMode] = useState(() => loadDeveloperMode());

  useEffect(() => {
    if (open) setDeveloperMode(loadDeveloperMode());
  }, [open]);

  function toggleDeveloperMode() {
    const next = !developerMode;
    setDeveloperMode(next);
    saveDeveloperMode(next);
  }

  return (
    <Modal open={open} title="Settings" onClose={onClose}>
      <div className="space-y-4">
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-zinc-100">Developer Mode</p>
              <p className="mt-1 text-xs leading-relaxed text-zinc-400">
                When off, only business answers are shown. When on, each reply
                includes a collapsible Technical Details section (SQL, tools,
                model, timing, and routing).
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={developerMode}
              aria-label="Toggle Developer Mode"
              onClick={toggleDeveloperMode}
              className={`relative mt-0.5 h-6 w-11 shrink-0 rounded-full transition ${
                developerMode ? "bg-sky-500" : "bg-zinc-700"
              }`}
            >
              <span
                className={`absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white transition ${
                  developerMode ? "translate-x-5" : "translate-x-0"
                }`}
              />
            </button>
          </div>
          <p className="mt-3 text-[11px] text-zinc-500">
            Default: Off — Microsoft Copilot-style experience for normal users.
          </p>
        </div>
      </div>
    </Modal>
  );
}

import type { SuggestionChip } from "@/types";
import { SEMICONDUCTOR_CHIPS } from "@/constants/branding";

interface SuggestionChipsProps {
  onSelect: (prompt: string) => void;
  disabled?: boolean;
  items?: readonly SuggestionChip[] | readonly { label: string; prompt: string }[];
}

export function SuggestionChips({
  onSelect,
  disabled = false,
  items = SEMICONDUCTOR_CHIPS,
}: SuggestionChipsProps) {
  return (
    <div className="flex flex-wrap justify-center gap-2">
      {items.map((chip) => (
        <button
          key={chip.label}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(chip.prompt)}
          className="rounded-full border border-cyan-400/40 bg-transparent px-3.5 py-1.5 text-xs text-cyan-100/90 transition hover:border-cyan-300 hover:bg-cyan-400/10 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          {chip.label}
        </button>
      ))}
    </div>
  );
}

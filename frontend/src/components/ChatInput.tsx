import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { SendHorizontal } from "lucide-react";
import {
  useEffect,
  useRef,
  type FormEvent,
  type KeyboardEvent,
} from "react";

interface ChatInputProps {
  value: string;
  loading: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
}

export function ChatInput({ value, loading, onChange, onSubmit }: ChatInputProps) {
  const ref = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "0px";
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [value]);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSubmit();
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mx-auto flex w-full max-w-3xl items-end gap-2 rounded-full border border-cyan-400/30 bg-[#07111f]/75 p-1.5 pl-4 shadow-[0_0_28px_rgba(34,211,238,0.12)] backdrop-blur-xl"
    >
      <Textarea
        ref={ref}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask anything about your connected data..."
        disabled={loading}
        rows={1}
        aria-label="Ask Azure Data Copilot"
        className="min-h-[44px] border-0 bg-transparent px-1 py-3 shadow-none focus:ring-0"
      />
      <Button
        type="submit"
        size="icon"
        disabled={loading || !value.trim()}
        aria-label="Send message"
        className="mb-0.5 mr-0.5 h-11 w-11 shrink-0 rounded-full bg-zinc-600 text-white shadow-[0_0_20px_rgba(113,113,122,0.45)] hover:bg-zinc-500"
      >
        <SendHorizontal className="h-4 w-4" />
      </Button>
    </form>
  );
}

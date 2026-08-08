export function TypingIndicator() {
  return (
    <div
      className="mx-auto flex w-full max-w-3xl justify-start px-4"
      role="status"
      aria-live="polite"
      aria-label="Assistant is typing"
    >
      <div className="rounded-2xl border border-cyan-400/30 bg-[#07111f]/80 px-4 py-3 shadow-[0_0_24px_rgba(34,211,238,0.1)] backdrop-blur-md">
        <div className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-cyan-300 [animation-delay:-0.3s]" />
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-cyan-300 [animation-delay:-0.15s]" />
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-cyan-300" />
        </div>
      </div>
    </div>
  );
}

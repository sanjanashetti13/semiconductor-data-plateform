/** Strip embedded technical sections from older assistant markdown. */
export function toBusinessAnswer(content: string): string {
  let text = content;

  // Remove "## SQL Used" (or "**SQL Used**") blocks including fenced code.
  text = text.replace(
    /(?:^|\n)#{1,3}\s*SQL Used[\s\S]*?(?=(?:\n#{1,3}\s+)|\n\*\*[A-Z][^*]+\*\*|$)/gi,
    "\n",
  );
  text = text.replace(
    /(?:^|\n)\*\*SQL Used\*\*[\s\S]*?(?=(?:\n#{1,3}\s+)|\n\*\*[A-Z][^*]+\*\*|$)/gi,
    "\n",
  );
  text = text.replace(/```sql[\s\S]*?```/gi, "");

  return text.replace(/\n{3,}/g, "\n\n").trim();
}

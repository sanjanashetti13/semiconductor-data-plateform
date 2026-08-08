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

  // Strip leftover technical footers that may appear in older answers.
  text = text.replace(
    /(?:^|\n)\*\*(?:Tool|Router|Execution Time|Validation|Data Source)\*\*:?.*$/gim,
    "",
  );
  text = text.replace(
    /(?:^|\n)(?:Tool used|Router decision|Execution time|Query validation)\s*:.*$/gim,
    "",
  );

  return text.replace(/\n{3,}/g, "\n\n").trim();
}

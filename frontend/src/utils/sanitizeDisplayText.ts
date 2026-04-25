/** Plain text for feed: strip code fences, LaTeX, thinking tags, and obvious JSON dump lines. */
const FENCE = /```[\s\S]*?```/g;
const DD = /\$\$[\s\S]*?\$\$/g;
const INLINE = /\$([^\$\n]+?)\$/g;
const THINK = /<think>[\s\S]*?<\/redacted_thinking>|<thinking>[\s\S]*?<\/thinking>/gi;
export function sanitizeDisplayText(text: string): string {
  if (!text) return '';
  let t = String(text);
  t = t.replace(THINK, '');
  t = t.replace(FENCE, '');
  t = t.replace(DD, '');
  t = t.replace(INLINE, '');
  const lines = t.split('\n').filter((line) => {
    const s = line.trim();
    if (s.length <= 50) return true;
    if ((s.startsWith('{') && s.endsWith('}')) || (s.startsWith('[') && s.endsWith(']')))
      return false;
    return true;
  });
  t = lines.join('\n');
  t = t.replace(/\n{3,}/g, '\n\n');
  return t.trim();
}

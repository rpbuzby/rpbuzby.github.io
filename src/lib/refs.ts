/** Pull the "## References" list out of an article body so it can render after the author card.
 *  Returns each reference as an HTML string (links made clickable, emphasis kept). */
export function splitReferences(body: string): string[] {
  const m = body.match(/^## References\s*$/m);
  if (!m || m.index === undefined) return [];
  const tail = body.slice(m.index + m[0].length);
  return tail
    .split(/\n/)
    .map((l) => l.trim())
    .filter((l) => l.startsWith('- '))
    .map((l) => l.slice(2))
    .map((l) =>
      l
        .replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/\\([\[\]$])/g, '$1')
        .replace(/\*([^*]+)\*/g, '<em>$1</em>')
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
        .replace(/&lt;(https?:\/\/[^\s>]+)>/g, (_s, u) => `<a href="${u}" target="_blank" rel="noopener">${u.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '')}</a>`)
        .replace(/(^|[\s(])(https?:\/\/[^\s)]+)/g, (_s, pre, u) => `${pre}<a href="${u}" target="_blank" rel="noopener">${u.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '')}</a>`),
    );
}

/** Exact tag recurrence across distinct, recent saved dreams; no inferred diagnosis. */
export const normalizeTag = (tag: string) => tag.normalize('NFKC').toLocaleLowerCase('tr-TR').trim().replace(/\s+/g, ' ');

export function recurringThemes(dreams: { id: string; tags: string[] }[]) {
  const counts = new Map<string, number>();
  const seen = new Set<string>();
  for (const dream of dreams) {
    if (seen.has(dream.id)) continue;
    if (seen.size >= 15) break;
    seen.add(dream.id);
    const tags = new Set(dream.tags.map(normalizeTag).filter(tag => tag && tag.length <= 40));
    for (const tag of tags) counts.set(tag, (counts.get(tag) ?? 0) + 1);
  }
  return [...counts].filter(([, count]) => count >= 2).sort((a,b) => b[1] - a[1] || a[0].localeCompare(b[0], 'tr-TR'))
    .slice(0, 4).map(([label, count]) => ({ label, count }));
}

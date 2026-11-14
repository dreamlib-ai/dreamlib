export type Visibility = 'private' | 'public';
/** F5: typical dream themes (docs/arastirma/temalar.md keys) the dreamer says they have seen; optional. */
export const typicalThemes = ['chased', 'falling', 'flying', 'school', 'late', 'lost', 'teeth', 'water', 'house_rooms', 'deceased_visit', 'animals', 'naked_public'] as const;
export type TypicalTheme = typeof typicalThemes[number];
export type Profile = { onboarded: boolean; visibility: Visibility; seenThemes?: TypicalTheme[] };
export const defaultProfile: Profile = { onboarded: false, visibility: 'private' };

// Preferences are editable by the owner and never used for authorization.
export function profileFromMetadata(metadata: Record<string, unknown>): Profile {
  const saved = metadata.dreamlib;
  if (!saved || typeof saved !== 'object') return { ...defaultProfile };
  const value = saved as Record<string, unknown>;
  const seen = Array.isArray(value.seenThemes) ? value.seenThemes.filter((t): t is TypicalTheme => (typicalThemes as readonly unknown[]).includes(t)) : [];
  return { onboarded: value.onboarded === true, visibility: value.visibility === 'public' ? 'public' : 'private', ...(seen.length ? { seenThemes: [...new Set(seen)] } : {}) };
}

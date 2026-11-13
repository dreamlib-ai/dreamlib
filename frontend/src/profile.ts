export type Visibility = 'private' | 'public';
export type Profile = { onboarded: boolean; visibility: Visibility };
export const defaultProfile: Profile = { onboarded: false, visibility: 'private' };

// Preferences are editable by the owner and never used for authorization.
export function profileFromMetadata(metadata: Record<string, unknown>): Profile {
  const saved = metadata.dreamlib;
  if (!saved || typeof saved !== 'object') return { ...defaultProfile };
  const value = saved as Record<string, unknown>;
  return { onboarded: value.onboarded === true, visibility: value.visibility === 'public' ? 'public' : 'private' };
}

export const appearanceOptions = {
  skin:['light','warm','olive','deep'], face:['oval','round','angular'], hair:['short','curly','wavy','long','bun','none'],
  hairColor:['brown','black','copper','blond','grey'], build:['slim','average','broad'], outfit:['jacket','sweater','shirt'],
  outfitColor:['midnight','sage','cobalt','cream'], accessory:['none','glasses','earrings'], expression:['calm','curious','smile'], pose:['relaxed','folded','hands-front'],
} as const;
export type AvatarSpec = { [K in keyof typeof appearanceOptions]: typeof appearanceOptions[K][number] };
export type PresetId = 'dawn' | 'moss' | 'copper' | 'ink';
export const presetIds: PresetId[] = ['dawn','moss','copper','ink'];
export const defaultAvatar: AvatarSpec = { skin:'warm',face:'oval',hair:'short',hairColor:'brown',build:'average',outfit:'jacket',outfitColor:'midnight',accessory:'none',expression:'calm',pose:'relaxed' };
export type AvatarDraft = { id:string; spec:AvatarSpec; baseRevision:number };
const prefix = 'dreamlib:avatar-draft:v1:';
export function readAvatarDraft(owner:string):AvatarDraft|null {
  try {
    const raw=localStorage.getItem(prefix+owner);
    if (!raw) return null;
    if(raw.length>4000)throw new Error('oversize');
    const {updatedAt,value}=JSON.parse(raw);
    if (!Number.isFinite(updatedAt) || Date.now()-updatedAt>86400000 || updatedAt>Date.now()+60000
      || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value?.id) || !Number.isInteger(value.baseRevision) || value.baseRevision<0
      || !Object.entries(appearanceOptions).every(([key,allowed]) => (allowed as readonly string[]).includes(value.spec?.[key]))) throw new Error('invalid');
    return value;
  } catch { clearAvatarDraft(owner); return null; }
}
export function writeAvatarDraft(owner:string,value:AvatarDraft):boolean {
  try { localStorage.setItem(prefix+owner,JSON.stringify({updatedAt:Date.now(),value})); return true; } catch { return false; }
}
export function clearAvatarDraft(owner:string) { try { localStorage.removeItem(prefix+owner); } catch { /* storage can be unavailable */ } }

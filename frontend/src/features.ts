import type { Analysis, Dream, Experience, Genre, Perspective } from './api';

export const genres: Genre[] = ['daily', 'fantasy', 'scifi', 'romance', 'adventure', 'suspense'];
export const perspectives: Perspective[] = ['unknown', 'first-person', 'observer', 'mixed'];
export const experiences: Experience[] = ['lucid', 'recurring', 'nightmare'];

/** Null means no override; [] is an intentional user correction to no labels. */
export function effectiveFeatures(dream: Analysis & Pick<Partial<Dream>, 'journal'>) {
  const model = dream.features;
  const override = dream.journal?.classification;
  return {
    version: model?.version ?? 0,
    genres: [...new Set(override?.genres ?? model?.genres ?? [])].filter(g => genres.includes(g)),
    perspective: perspectives.includes(override?.perspective ?? model?.perspective ?? 'unknown') ? override?.perspective ?? model?.perspective ?? 'unknown' : 'unknown',
    experiences: [...new Set(override?.experiences ?? model?.experiences?.map(e => e.kind) ?? [])].filter(e => experiences.includes(e)),
    tags: [...new Set(override?.tags ?? dream.tags)],
    genreSource: override?.genres != null ? 'user' : 'model',
    experienceSource: override?.experiences != null ? 'user' : 'narrative',
    perspectiveSource: override?.perspective != null ? 'user' : 'model',
    tagsSource: override?.tags != null ? 'user' : 'model',
  };
}

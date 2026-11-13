"""Small, versioned narrative features; experience claims require explicit quoted evidence."""
import unicodedata
from typing import Annotated, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, StringConstraints

Genre = Literal['daily', 'fantasy', 'scifi', 'romance', 'adventure', 'suspense']
Perspective = Literal['first-person', 'observer', 'mixed', 'unknown']
Experience = Literal['lucid', 'recurring', 'nightmare']
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class ExperienceEvidence(BaseModel):
    kind: Experience = Field(validation_alias=AliasChoices('kind', 'type'))
    quote: str = Field(max_length=200)


class Features(BaseModel):
    version: int = Field(default=0, ge=0, le=1)
    genres: list[Genre] = Field(default_factory=list, max_length=6)
    perspective: Perspective = 'unknown'
    people: list[ShortText] = Field(default_factory=list, max_length=12)
    places: list[ShortText] = Field(default_factory=list, max_length=12)
    events: list[ShortText] = Field(default_factory=list, max_length=12)
    experiences: list[ExperienceEvidence] = Field(default_factory=list, max_length=3)


class ClassificationOverride(BaseModel):
    model_config = ConfigDict(extra='forbid')
    genres: list[Genre] | None = Field(default=None, max_length=6)
    perspective: Perspective | None = None
    experiences: list[Experience] | None = Field(default=None, max_length=3)
    tags: list[ShortText] | None = Field(default=None, max_length=20)


def normalized(text: str) -> str:
    return ' '.join(unicodedata.normalize('NFKC', text).translate(str.maketrans('Iİ', 'ıi')).lower().split())


MARKERS = {
    'lucid': ('rüyada olduğumu', 'rüya gördüğümü fark', 'rüya gördüğümün fark', 'rüya olduğunu fark', 'knew i was dreaming', 'realized i was dreaming', 'realised i was dreaming', 'lucid dream'),
    'recurring': ('bu rüyayı daha önce', 'aynı rüyayı tekrar', 'yine aynı rüy', 'same dream again', 'recurring dream', 'repeated dream'),
    'nightmare': ('kâbus', 'kabus', 'nightmare'),
}


def grounded_features(features: Features, text: str) -> Features:
    result = features.model_copy(deep=True)
    result.genres = list(dict.fromkeys(result.genres))
    narrative = normalized(text)
    seen = set()
    supported = []
    for entry in result.experiences:
        quote = normalized(entry.quote)
        negative = any(word in quote for word in ('değildi', 'etmedim', 'bilmiyordum', 'did not', "wasn't", 'not a nightmare'))
        if quote and quote in narrative and not negative and entry.kind not in seen and any(marker in quote for marker in MARKERS[entry.kind]):
            supported.append(entry)
            seen.add(entry.kind)
    result.experiences = supported
    for field in ('people', 'places', 'events'):
        values = getattr(result, field)
        setattr(result, field, list(dict.fromkeys(v.strip()[:80] for v in values if v.strip())))
    return result

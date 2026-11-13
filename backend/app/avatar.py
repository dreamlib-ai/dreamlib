"""Private avatar appearance and fixed, versioned starter characters."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

PresetId = Literal['dawn', 'moss', 'copper', 'ink']


class AvatarSpec(BaseModel):
    model_config = ConfigDict(extra='forbid')
    skin: Literal['light','warm','olive','deep'] = 'warm'
    face: Literal['oval','round','angular'] = 'oval'
    hair: Literal['short','curly','wavy','long','bun','none'] = 'short'
    hairColor: Literal['brown','black','copper','blond','grey'] = 'brown'
    build: Literal['slim','average','broad'] = 'average'
    outfit: Literal['jacket','sweater','shirt'] = 'jacket'
    outfitColor: Literal['midnight','sage','cobalt','cream'] = 'midnight'
    accessory: Literal['none','glasses','earrings'] = 'none'
    expression: Literal['calm','curious','smile'] = 'calm'
    pose: Literal['relaxed','folded','hands-front'] = 'relaxed'


PRESETS = {
    'dawn': AvatarSpec(),
    'moss': AvatarSpec(skin='deep',face='angular',hair='curly',hairColor='black',outfit='sweater',outfitColor='sage'),
    'copper': AvatarSpec(skin='light',face='round',hair='wavy',hairColor='copper',outfit='shirt',outfitColor='cobalt'),
    'ink': AvatarSpec(skin='olive',hair='bun',hairColor='black',outfit='shirt',outfitColor='cream',accessory='glasses'),
}


class SelfProfile(BaseModel):
    id: str
    displayName: str = ''
    avatar: AvatarSpec | None = None
    presetId: PresetId | None = None
    avatarPath: str = ''
    revision: int = 0


def avatar_prompt(spec: AvatarSpec) -> str:
    return ('A fully clothed adult human character reference, full body front view with head and shoes visible. '
            'Mature editorial dry pastel illustration, tactile paper grain, navy shadows and warm highlights. '
            'Plain neutral background, no scenery, props, text, watermark or signature. '
            'Show the same recognizable individual in a relaxed clear reference pose, with these requested appearance properties: '
            + ', '.join(f'{key}: {value}' for key,value in spec.model_dump().items()) + '.')

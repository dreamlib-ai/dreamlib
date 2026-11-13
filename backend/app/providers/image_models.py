"""The fal model registry: image_models.toml, one block per model under a name we choose.

Settings name a model by that name or by its full fal id. A full id missing from the registry still
works (with a warning and zero price) so trying a new model never needs a code change."""
import logging
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("dreamlib")

DEFAULT_FILE = Path(__file__).with_name("image_models.toml")
ROLES = ("image", "edit", "speech")


@dataclass(frozen=True)
class FalModel:
    name: str
    id: str
    role: str
    price: float = 0.0
    typical_seconds: float = 10.0
    enabled: bool = True


def load(path: Path | None = None) -> dict[str, FalModel]:
    path = path or Path(os.environ.get("DREAMLIB_IMAGE_MODELS") or DEFAULT_FILE)
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    models = {}
    for name, block in raw.items():
        m = FalModel(name=name, id=block["id"], role=block["role"], price=float(block.get("price", 0)),
                     typical_seconds=float(block.get("typical_seconds", 10)), enabled=bool(block.get("enabled", True)))
        if m.role not in ROLES:
            raise ValueError(f"image_models: {name} has unknown role {m.role!r}")
        models[name] = m
    return models


def resolve(choice: str, role: str, models: dict[str, FalModel] | None = None) -> FalModel:
    """The model a setting names, by our name or by fal id. Disabled or wrong-role entries are refused."""
    models = load() if models is None else models
    found = models.get(choice) or next((m for m in models.values() if m.id == choice), None)
    if found is None:
        log.warning("image_models: %s is not in the registry; price and time estimate unknown", choice)
        return FalModel(name=choice, id=choice, role=role)
    if not found.enabled:
        raise ValueError(f"image_models: {found.name} is disabled")
    if found.role != role:
        raise ValueError(f"image_models: {found.name} is a {found.role} model, not {role}")
    return found

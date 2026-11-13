import hashlib
import json

import pytest

from app.models import MangaMeta
from app.prompts import image
from app.providers.image_models import load, resolve


def test_registry_names_and_ids_both_resolve():
    models = load()
    assert {"fast", "quality", "consistent", "speech"} <= set(models)
    assert resolve("fast", "image").id == "fal-ai/flux/schnell"
    assert resolve("fal-ai/nano-banana/edit", "edit").name == "consistent"


def test_unknown_id_still_works_and_bad_choices_are_refused(tmp_path, monkeypatch):
    new = resolve("fal-ai/some-new-model", "image")
    assert (new.id, new.price) == ("fal-ai/some-new-model", 0.0)
    with pytest.raises(ValueError):
        resolve("consistent", "image")  # an edit model in the image slot

    custom = tmp_path / "models.toml"
    custom.write_text('[old]\nid = "fal-ai/old"\nrole = "image"\nenabled = false\n\n[mine]\nid = "fal-ai/mine"\nrole = "image"\nprice = 0.01\n', encoding="utf-8")
    monkeypatch.setenv("DREAMLIB_IMAGE_MODELS", str(custom))
    assert set(load()) == {"old", "mine"} and resolve("mine", "image").price == 0.01
    with pytest.raises(ValueError):
        resolve("old", "image")


# A revision's text never changes once used; add a new revision instead. When adding one, pin it here.
PINNED = {"image@1": "4725d6eb0c1b"}


def digest(rev: dict) -> str:
    return hashlib.sha256(json.dumps(rev, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]


def test_image_prompt_revisions_are_frozen():
    assert set(image.REVISIONS) == set(PINNED) and image.LATEST in PINNED
    for version, pinned in PINNED.items():
        assert digest(image.REVISIONS[version]) == pinned, f"{version} was edited: add a new revision instead"


def test_new_jobs_use_the_chosen_revision_and_old_ones_keep_theirs(monkeypatch):
    assert image.active() == image.LATEST
    monkeypatch.setenv("DREAMLIB_IMAGE_PROMPT", "image@9")
    with pytest.raises(ValueError):
        image.active()
    legacy = MangaMeta.model_validate({"Style": "manga"})  # stored before revisions were recorded
    assert legacy.prompt_version == "" and image.revision(legacy.prompt_version) is image.REVISIONS[image.LEGACY]

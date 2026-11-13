import hashlib

from app import prompts
from app.providers.openrouter import TASKS

# A prompt's text and its version change together. When this fails, bump VERSION in the prompt's
# file and update both columns here.
PINNED = {
    "clean": ("clean@1", "f7fdb8d0a250"),
    "interpret": ("interpret@1", "ad018c8e7bc0"),
    "storyboard": ("storyboard@1", "0435565ec848"),
}


def text(task: str) -> str:
    return {"clean": prompts.CLEAN_SYSTEM, "interpret": prompts.ANALYZE_SYSTEM, "storyboard": prompts.storyboard_prompt(4)}[task]


def test_every_prompt_is_pinned_to_its_version():
    assert set(prompts.VERSIONS) == set(PINNED) and set(PINNED) <= set(TASKS)
    for task, (version, digest) in PINNED.items():
        assert prompts.VERSIONS[task] == version
        assert hashlib.sha256(text(task).encode()).hexdigest()[:12] == digest, f"{task} changed: bump its VERSION"

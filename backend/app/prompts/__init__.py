"""Prompts, one file per LLM task, each with a version id (docs/llm.md).

Change a prompt's text and bump its VERSION together; tests/test_prompts.py pins both."""
from . import clean, interpret, storyboard
from .clean import CLEAN_SYSTEM
from .interpret import ANALYZE_SYSTEM
from .storyboard import storyboard_prompt
from .tables import INTERPRETATION_HINTS, STYLE_HINTS

VERSIONS = {"clean": clean.VERSION, "interpret": interpret.VERSION, "storyboard": storyboard.VERSION}

__all__ = ["ANALYZE_SYSTEM", "CLEAN_SYSTEM", "INTERPRETATION_HINTS", "STYLE_HINTS", "VERSIONS", "storyboard_prompt"]

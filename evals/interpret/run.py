"""Run the interpretation prompt against fixed synthetic narratives (paid, explicit --live).

Run with the backend's Python and the configured OpenRouter environment. Save each
prompt version to a separate JSONL file, then use the review notes to compare prose.
This isolates the prompt for a new journal: no history, lexicon, persistence or ASR.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "backend"))

from app.config import llm_routes
from app.models import Analysis
from app.prompts import ANALYZE_SYSTEM, INTERPRETATION_HINTS, VERSIONS
from app.providers.openrouter import OpenRouter
from app.services import extract_json
from app.usage import MemoryUsage, Meter


async def measure(output: Path) -> None:
    cases = [json.loads(line) for line in (HERE / "cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    env = os.environ.get
    llm = OpenRouter(env("OPENROUTER_API_KEY", ""), env("OPENROUTER_MODEL", ""), llm_routes(env))
    usage = MemoryUsage()
    llm.meter = Meter(usage)
    try:
        if not llm.enabled or not llm.models_for("interpret"):
            raise SystemExit("The OpenRouter interpretation environment is not configured.")
        with output.open("x", encoding="utf-8") as report:
            for case in cases:
                usage.rows.clear()
                started = time.monotonic()
                messages = [
                    {"role": "system", "content": ANALYZE_SYSTEM + "\n\n" + INTERPRETATION_HINTS["universal"]},
                    {"role": "user", "content": case["text"]},
                ]
                row = {"id": case["id"], "prompt": VERSIONS["interpret"], "review": case["review"]}
                try:
                    reply = "".join([part async for part in llm.stream(messages, task="interpret", schema=Analysis)])
                    analysis = Analysis.model_validate(extract_json(reply))
                    row["result"] = analysis.model_dump(mode="json")
                except Exception as error:
                    row["error"] = type(error).__name__
                row["seconds"] = round(time.monotonic() - started, 2)
                if usage.rows:
                    row.update({key: usage.rows[-1][key] for key in ("model", "units", "cost_usd")})
                print(json.dumps(row, ensure_ascii=False), file=report, flush=True)
                print(case["id"], "ok" if "result" in row else row["error"], row["seconds"], flush=True)
    finally:
        await llm.http.aclose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="make eight paid calls with the synthetic cases")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.live:
        parser.error("--live is required to run this comparison")
    asyncio.run(measure(args.output))

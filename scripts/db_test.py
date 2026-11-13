"""Real database tests on a throwaway copy, `dreamlib-local-test`: built from the migrations exactly as
`dreamlib-local` is (scripts/local_db.py), so your local data is never touched.

    python scripts/db_test.py           # build, test, delete
    python scripts/db_test.py --keep    # leave the test stack running (fast re-runs: --reuse)
    python scripts/db_test.py --reuse   # only run the tests against the running test stack

Needs Docker. The tests run with the backend's Python (backend/.venv, or DREAMLIB_PYTHON)."""
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from local_db import COMPOSE, ROOT, SECRET, Stack, up  # noqa: E402

TEST = Stack("dreamlib-local-test", 55442, 55443)


def backend_python() -> str:
    if os.environ.get("DREAMLIB_PYTHON"):
        return os.environ["DREAMLIB_PYTHON"]
    for p in (ROOT / "backend/.venv/Scripts/python.exe", ROOT / "backend/.venv/bin/python"):
        if p.exists():
            return str(p)
    return sys.executable


def main() -> int:
    keep, reuse = "--keep" in sys.argv, "--reuse" in sys.argv
    passthrough = [a for a in sys.argv[1:] if a not in ("--keep", "--reuse")]
    if not reuse:
        TEST.compose("down", "-v", check=False, capture_output=True)
        up(TEST)
    env = {**TEST.env(), "DREAMLIB_DB_TEST": "1", "DREAMLIB_DB_REST": TEST.rest_url, "DREAMLIB_DB_SECRET": SECRET,
           "DREAMLIB_DB_COMPOSE": str(COMPOSE), "DREAMLIB_DB_PROJECT": TEST.name}
    try:
        return subprocess.run([backend_python(), "-m", "pytest", "-q", "-m", "db", "tests/db", *passthrough],
                              cwd=ROOT / "backend", env=env).returncode
    finally:
        if not keep and not reuse:
            TEST.compose("down", "-v", check=False, capture_output=True)


if __name__ == "__main__":
    raise SystemExit(main())

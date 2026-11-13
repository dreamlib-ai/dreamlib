"""Real database tests: starts Supabase's Postgres image and PostgREST in Docker, applies every
migration in supabase/migrations in order, then runs the tests marked `db` against them.

    python scripts/db_test.py           # up, migrate, test, down
    python scripts/db_test.py --keep    # leave the stack running afterwards (fast re-runs: --reuse)
    python scripts/db_test.py --reuse   # skip start and migrations, only run the tests

Needs Docker. Uses only the standard library; the tests run with the backend's Python
(backend/.venv, or DREAMLIB_PYTHON)."""
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "supabase" / "test" / "compose.yml"
MIGRATIONS = ROOT / "supabase" / "migrations"
REST_URL = "http://127.0.0.1:55433"
SECRET = "dreamlib-local-test-secret-not-for-production-use"


def compose(*args: str, check: bool = True, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", "compose", "-f", str(COMPOSE), "--profile", "rest", *args], check=check, **kw)


def psql(sql: str | None = None, file: Path | None = None, user: str = "postgres") -> subprocess.CompletedProcess:
    cmd = ["exec", "-T", "db", "psql", "-U", user, "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-q"]
    if sql is not None:
        return compose(*cmd, "-c", sql, check=False, capture_output=True, text=True, encoding="utf-8")
    return compose(*cmd, check=False, capture_output=True, text=True, encoding="utf-8",
                   input=file.read_text(encoding="utf-8"))


def migrate() -> None:
    files = sorted(MIGRATIONS.glob("*.sql"))
    for f in files:
        res = psql(file=f)
        if res.returncode:
            print(f"migration failed: {f.name}\n{res.stderr.strip()}", file=sys.stderr)
            raise SystemExit(1)
        print(f"  applied {f.name}")
    psql("notify pgrst, 'reload schema'")
    print(f"{len(files)} migrations applied")


def wait_rest(seconds: float = 60) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(REST_URL + "/", timeout=2):
                return
        except Exception:
            time.sleep(1)
    raise SystemExit("PostgREST did not come up")


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
        compose("down", "-v", check=False, capture_output=True)
        print("starting Postgres")
        compose("up", "-d", "--wait", "db")
        res = psql("alter role authenticator with login password 'postgres';", user="supabase_admin")
        if res.returncode:
            print(res.stderr, file=sys.stderr)
            return 1
        res = psql(file=COMPOSE.with_name("bootstrap.sql"), user="supabase_admin")
        if res.returncode:
            print(res.stderr, file=sys.stderr)
            return 1
        migrate()
        print("starting PostgREST")
        compose("up", "-d", "rest")
        wait_rest()
    env = {**os.environ, "DREAMLIB_DB_TEST": "1", "DREAMLIB_DB_REST": REST_URL, "DREAMLIB_DB_SECRET": SECRET,
           "DREAMLIB_DB_COMPOSE": str(COMPOSE)}
    try:
        return subprocess.run([backend_python(), "-m", "pytest", "-q", "-m", "db", "tests/db", *passthrough],
                              cwd=ROOT / "backend", env=env).returncode
    finally:
        if not keep and not reuse:
            compose("down", "-v", check=False, capture_output=True)


if __name__ == "__main__":
    raise SystemExit(main())

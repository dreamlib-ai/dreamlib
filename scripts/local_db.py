"""The local database `dreamlib-local`: Supabase's Postgres image and PostgREST in Docker, kept
between runs, with migrations tracked like the Supabase CLI does (supabase_migrations.schema_migrations).

    python scripts/local_db.py up        # start (creating the database the first time) and apply pending migrations
    python scripts/local_db.py status    # applied and pending migrations
    python scripts/local_db.py migrate   # apply pending migrations only
    python scripts/local_db.py psql      # open a SQL shell
    python scripts/local_db.py down      # stop; data is kept
    python scripts/local_db.py reset     # delete the data and start again from the migrations

`npm run db -- <command>` does the same. Postgres listens on 127.0.0.1:55432, PostgREST on :55433.
Only the standard library is used."""
import os
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "supabase" / "local" / "compose.yml"
BOOTSTRAP = COMPOSE.with_name("bootstrap.sql")
MIGRATIONS = ROOT / "supabase" / "migrations"
SECRET = "dreamlib-local-test-secret-not-for-production-use"


@dataclass(frozen=True)
class Stack:
    name: str  # compose project name and database name
    db_port: int
    rest_port: int

    @property
    def rest_url(self) -> str:
        return f"http://127.0.0.1:{self.rest_port}"

    def env(self) -> dict:
        return {**os.environ, "DREAMLIB_DB_NAME": self.name, "DREAMLIB_DB_PORT": str(self.db_port),
                "DREAMLIB_REST_PORT": str(self.rest_port)}

    def compose(self, *args: str, check: bool = True, **kw) -> subprocess.CompletedProcess:
        return subprocess.run(["docker", "compose", "-p", self.name, "-f", str(COMPOSE), "--profile", "rest", *args],
                              check=check, env=self.env(), **kw)

    def psql(self, sql: str | None = None, file: Path | None = None, user: str = "postgres",
             database: str | None = None, tuples: bool = False) -> subprocess.CompletedProcess:
        cmd = ["exec", "-T", "db", "psql", "-U", user, "-d", database or self.name, "-v", "ON_ERROR_STOP=1", "-q"]
        if tuples:
            cmd.append("-At")
        kw = dict(check=False, capture_output=True, text=True, encoding="utf-8")
        if sql is not None:
            return self.compose(*cmd, "-c", sql, **kw)
        return self.compose(*cmd, input=file.read_text(encoding="utf-8"), **kw)

    def must(self, res: subprocess.CompletedProcess, what: str) -> str:
        if res.returncode:
            print(f"{what} failed:\n{res.stderr.strip()}", file=sys.stderr)
            raise SystemExit(1)
        return res.stdout.strip()


LOCAL = Stack("dreamlib-local", 55432, 55433)


def exists(stack: Stack) -> bool:
    res = stack.psql(f"select 1 from pg_database where datname = '{stack.name}'", database="postgres", tuples=True)
    return res.stdout.strip() == "1"


def create(stack: Stack) -> None:
    """The database is a copy of `postgres`, which the Supabase image fills with auth, storage and extensions."""
    stack.must(stack.psql("alter role authenticator with login password 'postgres';", user="supabase_admin", database="postgres"),
               "authenticator role")
    # Supabase's background workers keep sessions open on `postgres`, and a template must have none:
    # stop new connections, end the open ones, copy, then let them back in.
    copy = "\n".join([
        "alter database postgres allow_connections false;",
        "select pg_terminate_backend(pid) from pg_stat_activity where datname = 'postgres' and pid <> pg_backend_pid();",
        "select pg_sleep(0.5);",
        f'create database "{stack.name}" owner postgres template postgres;',
    ]) + "\n"
    res = None
    for _ in range(5):
        res = stack.compose("exec", "-T", "db", "psql", "-U", "supabase_admin", "-d", "template1", "-v", "ON_ERROR_STOP=1", "-q",
                            check=False, capture_output=True, text=True, encoding="utf-8", input=copy)
        if res.returncode == 0:
            break
        time.sleep(1)
    stack.psql("alter database postgres allow_connections true;", user="supabase_admin", database="template1")
    stack.must(res, "create database")
    stack.must(stack.psql(file=BOOTSTRAP, user="supabase_admin"), "bootstrap")
    stack.must(stack.psql("create schema if not exists supabase_migrations; "
                          "create table if not exists supabase_migrations.schema_migrations "
                          "(version text primary key, name text not null, applied_at timestamptz not null default now());"),
               "migration table")
    print(f"created database {stack.name}")


def applied(stack: Stack) -> set[str]:
    out = stack.must(stack.psql("select version from supabase_migrations.schema_migrations", tuples=True), "status")
    return set(out.split())


def pending(stack: Stack) -> list[Path]:
    done = applied(stack)
    return [f for f in sorted(MIGRATIONS.glob("*.sql")) if f.name.split("_", 1)[0] not in done]


def migrate(stack: Stack) -> int:
    todo = pending(stack)
    for f in todo:
        version, name = f.stem.split("_", 1)
        # The migration and its bookkeeping row go in together, or neither does.
        sql = f.read_text(encoding="utf-8")
        script = f"begin;\n{sql}\n;\ninsert into supabase_migrations.schema_migrations (version, name) values ('{version}', '{name}');\ncommit;\n"
        res = stack.compose("exec", "-T", "db", "psql", "-U", "postgres", "-d", stack.name, "-v", "ON_ERROR_STOP=1", "-q",
                            check=False, capture_output=True, text=True, encoding="utf-8", input=script)
        if res.returncode:
            print(f"migration failed: {f.name}\n{res.stderr.strip()}", file=sys.stderr)
            raise SystemExit(1)
        print(f"  applied {f.name}")
    stack.psql("notify pgrst, 'reload schema'")
    print(f"{len(todo)} migration(s) applied" if todo else "migrations up to date")
    return len(todo)


def wait_rest(stack: Stack, seconds: float = 60) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(stack.rest_url + "/", timeout=2):
                return
        except Exception:
            time.sleep(1)
    raise SystemExit("PostgREST did not come up")


def up(stack: Stack) -> None:
    stack.compose("up", "-d", "--wait", "db")
    if not exists(stack):
        create(stack)
    migrate(stack)
    stack.compose("up", "-d", "rest")
    wait_rest(stack)
    print(f"{stack.name}: postgres 127.0.0.1:{stack.db_port}, rest {stack.rest_url}")


def status(stack: Stack) -> None:
    if not exists(stack):
        print(f"{stack.name} does not exist yet: run `up`")
        return
    done = applied(stack)
    for f in sorted(MIGRATIONS.glob("*.sql")):
        print(("applied  " if f.name.split("_", 1)[0] in done else "PENDING  ") + f.name)


def main() -> int:
    cmd = (sys.argv[1:] or ["up"])[0]
    stack = LOCAL
    if cmd == "up":
        up(stack)
    elif cmd == "migrate":
        migrate(stack)
    elif cmd == "status":
        status(stack)
    elif cmd == "down":
        stack.compose("stop")
    elif cmd == "reset":
        stack.compose("down", "-v")
        up(stack)
    elif cmd == "psql":
        return subprocess.call(["docker", "compose", "-p", stack.name, "-f", str(COMPOSE), "exec", "db",
                                "psql", "-U", "postgres", "-d", stack.name], env=stack.env())
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

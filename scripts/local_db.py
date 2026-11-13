"""The local database `dreamlib-local`: Supabase's Postgres image and PostgREST in Docker, kept
between runs, with migrations tracked like the Supabase CLI does (supabase_migrations.schema_migrations).

    python scripts/local_db.py up        # start (creating the database the first time) and apply pending migrations
    python scripts/local_db.py app       # `up`, then the backend (:8080) and the frontend (:5173) in Docker too
    python scripts/local_db.py logs      # follow the logs (add service names: logs backend frontend)
    python scripts/local_db.py env       # the backend/.env and frontend/.env.local lines that point the app here
    python scripts/local_db.py status    # applied and pending migrations
    python scripts/local_db.py migrate   # apply pending migrations only
    python scripts/local_db.py psql      # open a SQL shell
    python scripts/local_db.py down      # stop; data is kept
    python scripts/local_db.py reset     # delete the data and start again from the migrations

`npm run db -- <command>` does the same. Postgres listens on 127.0.0.1:55432, PostgREST on :55433, and
the API on :55431: a gateway that serves PostgREST, GoTrue (sign-in) and storage-api (pictures) under
Supabase's own paths (/rest/v1, /auth/v1, /storage/v1), so the app runs against it unchanged.
Only the standard library is used."""
import base64
import hashlib
import hmac
import json
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


def local_key(role: str) -> str:
    """A Supabase-style API key (an HS256 JWT) signed with the local secret; valid nowhere else."""
    def b64(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    head = b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = b64(json.dumps({"role": role, "iss": "dreamlib-local", "iat": 1767225600, "exp": 2082758400},
                          separators=(",", ":")).encode())
    sig = b64(hmac.new(SECRET.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest())
    return f"{head}.{body}.{sig}"


ANON_KEY, SERVICE_KEY = local_key("anon"), local_key("service_role")
SECRETS = COMPOSE.with_name(".env")  # git-ignored: DREAMLIB_GOOGLE_ENABLED, _CLIENT_ID, _SECRET for local Google sign-in


def local_secrets() -> dict:
    """KEY=VALUE lines of supabase/local/.env; the shell's own variables win over them."""
    if not SECRETS.is_file():
        return {}
    out = {}
    for line in SECRETS.read_text(encoding="utf-8-sig").splitlines():
        key, sep, val = line.strip().partition("=")
        if sep and key and not key.startswith("#"):
            out[key.strip()] = val.strip().strip("\"'")
    return out


@dataclass(frozen=True)
class Stack:
    name: str  # compose project name and database name
    db_port: int
    rest_port: int
    api_port: int = 0  # 0: no sign-in, storage or gateway (the test stack)

    @property
    def rest_url(self) -> str:
        return f"http://127.0.0.1:{self.rest_port}"

    @property
    def api_url(self) -> str:
        return f"http://127.0.0.1:{self.api_port}"

    def env(self) -> dict:
        return {**local_secrets(), **os.environ, "DREAMLIB_DB_NAME": self.name, "DREAMLIB_DB_PORT": str(self.db_port),
                "DREAMLIB_REST_PORT": str(self.rest_port), "DREAMLIB_API_PORT": str(self.api_port or 55431),
                "DREAMLIB_ANON_KEY": ANON_KEY, "DREAMLIB_SERVICE_KEY": SERVICE_KEY}

    def profiles(self) -> list[str]:
        return ["--profile", "rest"] + (["--profile", "api", "--profile", "app"] if self.api_port else [])

    def compose(self, *args: str, check: bool = True, **kw) -> subprocess.CompletedProcess:
        return subprocess.run(["docker", "compose", "-p", self.name, "-f", str(COMPOSE), *self.profiles(), *args],
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


LOCAL = Stack("dreamlib-local", 55432, 55433, api_port=55431)


def exists(stack: Stack) -> bool:
    res = stack.psql(f"select 1 from pg_database where datname = '{stack.name}'", database="postgres", tuples=True)
    return res.stdout.strip() == "1"


def create(stack: Stack) -> None:
    """The database is a copy of `postgres`, which the Supabase image fills with auth, storage and extensions."""
    stack.must(stack.psql("alter role authenticator with login password 'postgres'; "
                          "alter role supabase_auth_admin with login password 'postgres'; "
                          "alter role supabase_storage_admin with login password 'postgres';",
                          user="supabase_admin", database="postgres"),
               "service roles")
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
    # Database-level grants are not copied from the template; Supabase gives these on `postgres`.
    stack.must(stack.psql(f'grant create, connect, temporary on database "{stack.name}" '
                          "to supabase_auth_admin, supabase_storage_admin;", user="supabase_admin"), "grants")
    if not stack.api_port:  # no storage-api here: stand in for the table it would create
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


def wait_http(url: str, what: str, seconds: float = 60) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return
        except Exception:
            time.sleep(1)
    raise SystemExit(f"{what} did not come up")


def running(stack: Stack, service: str) -> bool:
    res = stack.compose("ps", "-q", "--status", "running", service, check=False, capture_output=True, text=True)
    return bool(res.stdout.strip())


def up(stack: Stack) -> None:
    stack.compose("up", "-d", "--wait", "db")
    if not exists(stack):
        create(stack)
    if stack.api_port:
        # GoTrue and storage-api create their own tables (auth.*, storage.*) before the migrations use them.
        stack.compose("up", "-d", "--wait", "auth", "storage")
        # As on Supabase, the migrations' role may use the storage tables storage-api owns.
        stack.must(stack.psql("grant usage on schema storage to postgres, service_role; "
                              "grant all on all tables in schema storage to postgres, service_role; "
                              "grant all on all sequences in schema storage to postgres, service_role;",
                              user="supabase_admin"), "storage grants")
    migrate(stack)
    stack.compose("up", "-d", "rest", *(["gateway"] if stack.api_port else []))
    if stack.api_port and running(stack, "backend"):
        # The backend lives in the gateway's network; a new gateway container leaves it without one.
        stack.compose("up", "-d", "--no-deps", "--force-recreate", "backend")
        wait_http("http://127.0.0.1:8080/healthz", "backend")
    wait_http(stack.rest_url + "/", "PostgREST")
    line = f"{stack.name}: postgres 127.0.0.1:{stack.db_port}, rest {stack.rest_url}"
    if stack.api_port:
        wait_http(stack.api_url + "/auth/v1/health", "gateway")
        line += f", api {stack.api_url}"
    print(line)


def app(stack: Stack) -> None:
    """The whole app in Docker: the backend (code mounted, reloads on change) and the Vite dev server."""
    up(stack)
    stack.compose("up", "-d", "--build", "--force-recreate", "backend")
    print("frontend: installing packages and starting Vite (first run takes a minute)")
    stack.compose("up", "-d", "--wait", "frontend")
    wait_http("http://127.0.0.1:8080/healthz", "backend")
    print("app: http://localhost:5173  backend: http://127.0.0.1:8080/healthz (docs: /docs)")


def show_env(stack: Stack) -> None:
    print(f"""# backend/.env: the backend talks to {stack.name} (DREAMLIB_FAKE_AI must stay off with Supabase set)
SUPABASE_URL={stack.api_url}
SUPABASE_SERVICE_KEY={SERVICE_KEY}

# frontend/.env.local: guest and e-mail sign-in go to the local GoTrue (no Google here)
VITE_SUPABASE_URL={stack.api_url}
VITE_SUPABASE_ANON_KEY={ANON_KEY}""")


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
    elif cmd == "app":
        app(stack)
    elif cmd == "logs":
        return subprocess.call(["docker", "compose", "-p", stack.name, "-f", str(COMPOSE), *stack.profiles(),
                                "logs", "-f", "--tail", "50", *sys.argv[2:]], env=stack.env())
    elif cmd == "env":
        show_env(stack)
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
        return subprocess.call(["docker", "compose", "-p", stack.name, "-f", str(COMPOSE), *stack.profiles(), "exec", "db",
                                "psql", "-U", "postgres", "-d", stack.name], env=stack.env())
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

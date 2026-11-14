"""S3: frontend/src/generated/api.ts is what scripts/gen_client.py makes from today's schema."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_the_generated_client_is_current():
    spec = importlib.util.spec_from_file_location("gen_client", ROOT / "scripts" / "gen_client.py")
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    current = (ROOT / "frontend" / "src" / "generated" / "api.ts").read_text(encoding="utf-8")
    assert current == gen.render(gen.load_spec()), "run `npm run gen:api` and commit frontend/src/generated/api.ts"

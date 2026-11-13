import uvicorn

from .config import load_settings

host, _, port = load_settings().addr.rpartition(":")
uvicorn.run("app.main:app_factory", factory=True, host=host or "127.0.0.1", port=int(port))

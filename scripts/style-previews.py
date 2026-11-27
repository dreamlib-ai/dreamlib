"""Generate or publish the six synthetic thumbnails shown in the style picker.

Use the backend Python environment. Generate once with the configured FAL_IMAGE_MODEL,
inspect the output, then publish the same files from that directory with --publish.
"""
import argparse
import asyncio
from io import BytesIO
import os
from pathlib import Path
import sys

from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.prompts import image
from app.providers.fal import Fal
from app.providers.image_models import resolve
from app.store.supabase import Supabase

VERSION = "image@3"
BUCKET = "glyphs"  # Contains public, non-user illustrations.
PREFIX = "style-previews/v1"
SCENE = (
    "One person from behind in an ochre raincoat holding a red lantern at the end of a short stone jetty; "
    "a translucent blue whale under the clear still sea, a pale crescent in the navy sky. "
    "Balanced wide shot with the person and whale inside the central part of the frame."
)
MONO_SCENE = SCENE.replace("ochre raincoat", "dark raincoat").replace("red lantern", "glowing lantern").replace("blue whale", "whale").replace("navy sky", "night sky")


async def run(folder: Path, publish: bool) -> None:
    templates = image.REVISIONS[VERSION]
    fal = None if publish else Fal(os.environ["FAL_KEY"], resolve(os.environ.get("FAL_IMAGE_MODEL") or "fast", "image"))
    storage = Supabase(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    folder.mkdir(parents=True, exist_ok=True)
    gate = asyncio.Semaphore(3)

    async def one(style: str, description: str) -> None:
        path = folder / f"{style}.webp"
        async with gate:
            if publish:
                await storage.put_public(BUCKET, f"{PREFIX}/{path.name}", path.read_bytes(), "image/webp")
            elif not path.exists():
                prompt = templates["single"].format(style=description, prompt=MONO_SCENE if style == "manga" else SCENE)
                handle = await fal.submit(fal.image_body(prompt))
                urls = await fal.images(handle)
                raw = await storage.fetch(urls[0])
                with Image.open(BytesIO(raw)) as generated:
                    thumb = ImageOps.fit(generated.convert("RGB"), (480, 320), Image.Resampling.LANCZOS)
                    thumb.save(path, format="WEBP", quality=86)
            print(style, path.stat().st_size, "published" if publish else "ready", flush=True)

    try:
        if publish and not all((folder / f"{style}.webp").is_file() for style in templates["styles"]):
            raise SystemExit("All six reviewed thumbnails are required.")
        if fal:
            pending = sum(not (folder / f"{style}.webp").exists() for style in templates["styles"])
            print(f"Model: {fal.model}; estimate for {pending}: ${pending * fal.price:.3f}", flush=True)
        await asyncio.gather(*(one(style, description) for style, description in templates["styles"].items()))
    finally:
        await storage.http.aclose()
        if fal:
            await fal.http.aclose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--generate", action="store_true", help="make paid image requests")
    action.add_argument("--publish", action="store_true", help="upload reviewed public thumbnails")
    parser.add_argument("--folder", type=Path, required=True)
    flags = parser.parse_args()
    asyncio.run(run(flags.folder, flags.publish))

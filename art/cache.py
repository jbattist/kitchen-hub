from __future__ import annotations

import json
from pathlib import Path

from art.models import Artwork


class ArtCache:
    def __init__(self, cache_dir: str | Path) -> None:
        self.cache_dir = Path(cache_dir).expanduser()

    def write_metadata(self, artwork: Artwork) -> Path:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = self.cache_dir / f"{artwork.id}.json"
        metadata_path.write_text(json.dumps(artwork.to_dict(), indent=2), encoding="utf-8")
        return metadata_path

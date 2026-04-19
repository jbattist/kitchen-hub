from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Artwork:
    id: str
    title: str
    artist: str
    museum: str
    year: str
    image_url: str
    theme: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)

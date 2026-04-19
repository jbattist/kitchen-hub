from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SpotifySettings:
    client_id: str
    client_secret: str
    redirect_uri: str


@dataclass(frozen=True)
class SonosSettings:
    default_room: str
    rooms: list[str]


@dataclass(frozen=True)
class ArtSettings:
    idle_timeout_seconds: int
    slideshow_interval_seconds: int
    cache_dir: Path
    images_per_theme: int
    default_theme: str
    themes: list[str]


@dataclass(frozen=True)
class DisplaySettings:
    dim_after_seconds: int
    brightness_idle: int
    brightness_active: int


@dataclass(frozen=True)
class Settings:
    spotify: SpotifySettings
    sonos: SonosSettings
    art: ArtSettings
    display: DisplaySettings


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file {path} must contain a YAML mapping.")
    return data


def load_config(path: str | Path = "config.yaml") -> Settings:
    config_path = Path(path).expanduser()
    raw = _read_yaml(config_path)

    spotify = raw["spotify"]
    sonos = raw["sonos"]
    art = raw["art"]
    display = raw["display"]

    return Settings(
        spotify=SpotifySettings(
            client_id=spotify["client_id"],
            client_secret=spotify["client_secret"],
            redirect_uri=spotify["redirect_uri"],
        ),
        sonos=SonosSettings(
            default_room=sonos["default_room"],
            rooms=list(sonos["rooms"]),
        ),
        art=ArtSettings(
            idle_timeout_seconds=int(art["idle_timeout_seconds"]),
            slideshow_interval_seconds=int(art["slideshow_interval_seconds"]),
            cache_dir=Path(art["cache_dir"]).expanduser(),
            images_per_theme=int(art["images_per_theme"]),
            default_theme=art["default_theme"],
            themes=list(art["themes"]),
        ),
        display=DisplaySettings(
            dim_after_seconds=int(display["dim_after_seconds"]),
            brightness_idle=int(display["brightness_idle"]),
            brightness_active=int(display["brightness_active"]),
        ),
    )

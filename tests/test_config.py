from pathlib import Path

from app_config import load_config


def test_load_config_expands_cache_dir_and_preserves_theme_order(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
spotify:
  client_id: "client"
  client_secret: "secret"
  redirect_uri: "http://localhost:8888/callback"
sonos:
  default_room: "Kitchen"
  rooms:
    - "Kitchen"
    - "Living Room"
art:
  idle_timeout_seconds: 300
  slideshow_interval_seconds: 30
  cache_dir: "~/kitchen-hub-cache"
  images_per_theme: 25
  default_theme: "Impressionism"
  themes:
    - Impressionism
    - Abstract
display:
  dim_after_seconds: 600
  brightness_idle: 30
  brightness_active: 100
""".strip()
    )

    settings = load_config(config_path)

    assert settings.spotify.client_id == "client"
    assert settings.sonos.rooms == ["Kitchen", "Living Room"]
    assert settings.art.cache_dir.is_absolute()
    assert settings.art.cache_dir == Path("~/kitchen-hub-cache").expanduser()
    assert settings.art.themes == ["Impressionism", "Abstract"]

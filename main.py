from __future__ import annotations

from app_config import load_config
from art.fetcher import ArtService
from sonos.controller import SonosController
from spotify.client import SpotifyClient
from ui.app import create_app


def main() -> None:
    settings = load_config()
    spotify = SpotifyClient(settings.spotify)
    sonos = SonosController()
    app = create_app(
        spotify_client=spotify,
        art_service=ArtService(),
        sonos_controller=sonos,
        sonos_room=settings.sonos.default_room,
        idle_timeout_seconds=settings.art.idle_timeout_seconds,
        slideshow_interval_seconds=settings.art.slideshow_interval_seconds,
    )
    app.run(host="0.0.0.0", port=5000, debug=False)


if __name__ == "__main__":
    main()

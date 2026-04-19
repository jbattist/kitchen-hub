from __future__ import annotations

from typing import Any


class PlaybackController:
    def __init__(self, spotify_client: Any) -> None:
        self._spotify = spotify_client

    def current_playback(self) -> dict[str, Any]:
        return self._spotify.current_playback()

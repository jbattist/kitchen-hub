from __future__ import annotations

from typing import Any

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from app_config import SpotifySettings


class SpotifyClient:
    def __init__(self, settings: SpotifySettings) -> None:
        self._settings = settings
        self._client = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=settings.client_id,
                client_secret=settings.client_secret,
                redirect_uri=settings.redirect_uri,
                scope=" ".join(
                    [
                        "user-read-playback-state",
                        "user-modify-playback-state",
                        "user-read-currently-playing",
                        "playlist-read-private",
                    ]
                ),
            )
        )

    def current_playback(self) -> dict[str, Any]:
        payload = self._client.current_playback() or {}
        item = payload.get("item") or {}
        album = item.get("album") or {}
        images = album.get("images") or []
        return {
            "is_playing": payload.get("is_playing", False),
            "device_name": (payload.get("device") or {}).get("name"),
            "track": {
                "title": item.get("name"),
                "artist": ", ".join(artist["name"] for artist in item.get("artists", [])),
                "album": album.get("name"),
                "album_art_url": images[0]["url"] if images else None,
                "duration_ms": item.get("duration_ms"),
                "progress_ms": payload.get("progress_ms"),
            }
            if item
            else None,
        }

    def current_user_playlists(self) -> list[dict[str, Any]]:
        payload = self._client.current_user_playlists(limit=50)
        items = payload.get("items") or []
        return [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "uri": item.get("uri"),
                "image_url": ((item.get("images") or [{}])[0]).get("url"),
            }
            for item in items
        ]

    def start_playlist_playback(self, playlist_uri: str, device_name: str | None = None) -> dict[str, Any]:
        if device_name:
            devices = self._client.devices().get("devices") or []
            matching = next((device for device in devices if device.get("name") == device_name), None)
            if matching:
                self._client.transfer_playback(device_id=matching["id"])
                self._client.shuffle(state=True, device_id=matching["id"])
                self._client.start_playback(device_id=matching["id"], context_uri=playlist_uri)
                return {"ok": True, "device_name": device_name}

        self._client.shuffle(state=True)
        self._client.start_playback(context_uri=playlist_uri)
        return {"ok": True, "device_name": device_name}

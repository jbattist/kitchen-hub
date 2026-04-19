"""Tests for play/pause/skip controls and main.py wiring."""
from __future__ import annotations

import pytest

from ui.app import create_app
from art.themes import DEFAULT_THEMES


class StubSpotifyClient:
    def __init__(self) -> None:
        self._is_playing = True
        self.actions: list[str] = []
        self._playlists = [
            {
                "id": "p1",
                "name": "Morning Vibes",
                "uri": "spotify:playlist:p1",
                "image_url": "https://example.com/p1.jpg",
            }
        ]

    def current_playback(self):
        return {
            "is_playing": self._is_playing,
            "device_name": "Kitchen",
            "track": {
                "title": "Teardrop",
                "artist": "Massive Attack",
                "album": "Mezzanine",
                "album_art_url": "https://example.com/art.jpg",
                "duration_ms": 240000,
                "progress_ms": 60000,
            },
        }

    def current_user_playlists(self):
        return self._playlists

    def start_playlist_playback(self, playlist_uri: str, device_name: str | None = None):
        self.actions.append(f"play:{playlist_uri}")
        return {"ok": True}

    def pause(self) -> dict:
        self._is_playing = False
        self.actions.append("pause")
        return {"ok": True}

    def resume(self) -> dict:
        self._is_playing = True
        self.actions.append("resume")
        return {"ok": True}

    def next_track(self) -> dict:
        self.actions.append("next")
        return {"ok": True}

    def prev_track(self) -> dict:
        self.actions.append("prev")
        return {"ok": True}


class StubArtService:
    def get_next_artwork(self, theme_name=None):
        return {
            "id": "met-1",
            "title": "Water Lilies",
            "artist": "Monet",
            "museum": "Met",
            "year": "1906",
            "theme": theme_name or "Impressionism",
            "image_url": "https://images.metmuseum.org/1.jpg",
        }


class StubSonosController:
    def __init__(self) -> None:
        self.actions: list[str] = []

    def pause(self, room_name: str) -> dict:
        self.actions.append("pause")
        return {"ok": True}

    def resume(self, room_name: str) -> dict:
        self.actions.append("resume")
        return {"ok": True}

    def next_track(self, room_name: str) -> dict:
        self.actions.append("next")
        return {"ok": True}

    def prev_track(self, room_name: str) -> dict:
        self.actions.append("prev")
        return {"ok": True}


@pytest.fixture
def client_and_spotify():
    spotify = StubSpotifyClient()
    sonos = StubSonosController()
    app = create_app(
        spotify_client=spotify,
        art_service=StubArtService(),
        available_themes=DEFAULT_THEMES,
        sonos_controller=sonos,
        sonos_room="Kitchen",
    )
    return app.test_client(), spotify, sonos


def test_pause_endpoint(client_and_spotify):
    client, spotify, sonos = client_and_spotify
    response = client.post("/api/playback/pause")
    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
    assert "pause" in sonos.actions


def test_resume_endpoint(client_and_spotify):
    client, spotify, sonos = client_and_spotify
    response = client.post("/api/playback/resume")
    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
    assert "resume" in sonos.actions


def test_next_track_endpoint(client_and_spotify):
    client, spotify, sonos = client_and_spotify
    response = client.post("/api/playback/next")
    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
    assert "next" in sonos.actions


def test_prev_track_endpoint(client_and_spotify):
    client, spotify, sonos = client_and_spotify
    response = client.post("/api/playback/prev")
    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
    assert "prev" in sonos.actions


def test_status_includes_album_art_url(client_and_spotify):
    client, _, __ = client_and_spotify
    response = client.get("/api/status")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["playback"]["track"]["album_art_url"] == "https://example.com/art.jpg"


def test_index_renders_playback_controls(client_and_spotify):
    client, _, __ = client_and_spotify
    response = client.get("/")
    html = response.get_data(as_text=True)
    assert 'id="pause-button"' in html
    assert 'id="next-button"' in html
    assert 'id="prev-button"' in html
    assert 'id="album-art-img"' in html

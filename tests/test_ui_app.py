from __future__ import annotations

from ui.app import create_app, NoDeviceAvailableError
from art.themes import DEFAULT_THEMES


class StubSpotifyClient:
    def __init__(self, devices: list[dict] | None = None) -> None:
        self.playback_requests = []
        self._devices = devices if devices is not None else [
            {"id": "device-1", "name": "Kitchen", "type": "Speaker"},
            {"id": "device-2", "name": "Living Room", "type": "Speaker"},
        ]

    def current_playback(self):
        return {
            "is_playing": True,
            "device_name": "Kitchen",
            "track": {
                "title": "Teardrop",
                "artist": "Massive Attack",
                "album": "Mezzanine",
                "album_art_url": "https://example.com/art.jpg",
                "duration_ms": 240000,
                "progress_ms": 30000,
            },
        }

    def current_user_playlists(self):
        return [
            {
                "id": "playlist-1",
                "name": "Morning Vibes",
                "uri": "spotify:playlist:playlist-1",
                "image_url": "https://example.com/playlist-1.jpg",
            },
            {
                "id": "playlist-2",
                "name": "Jazz Evening",
                "uri": "spotify:playlist:playlist-2",
                "image_url": "https://example.com/playlist-2.jpg",
            },
        ]

    def list_devices(self) -> list[dict]:
        return self._devices

    def start_playlist_playback(self, playlist_uri: str, device_name: str | None = None):
        if not self._devices:
            raise NoDeviceAvailableError("No Spotify devices available")
        self.playback_requests.append(
            {"playlist_uri": playlist_uri, "device_name": device_name, "shuffle": True}
        )
        return {"ok": True}

    def pause(self):
        return {"ok": True}

    def resume(self):
        return {"ok": True}

    def next_track(self):
        return {"ok": True}

    def prev_track(self):
        return {"ok": True}


class StubArtService:
    def get_next_artwork(self, theme_name: str | None = None):
        return {
            "id": "met-42",
            "title": "Water Lilies",
            "artist": "Claude Monet",
            "museum": "The Metropolitan Museum of Art",
            "year": "1906",
            "theme": theme_name or "Impressionism",
            "image_url": "https://images.metmuseum.org/42.jpg",
        }


# ── helpers ──────────────────────────────────────────────────────────────────

class StubSonosController:
    def __init__(self, soco_ok: bool = True) -> None:
        self.soco_ok = soco_ok
        self.play_calls: list[dict] = []

    def pause(self, room_name: str) -> dict:
        return {"ok": True}

    def resume(self, room_name: str) -> dict:
        return {"ok": True}

    def next_track(self, room_name: str) -> dict:
        return {"ok": True}

    def prev_track(self, room_name: str) -> dict:
        return {"ok": True}

    def play_spotify_uri(self, uri: str, room_name: str) -> dict:
        self.play_calls.append({"uri": uri, "room_name": room_name})
        if self.soco_ok:
            return {"ok": True}
        return {"ok": False, "error": "Zone not found"}


def _make_client(devices=None, soco_ok: bool = False):
    """Create a test client. SoCo disabled by default so Spotify Connect path is testable."""
    sonos = StubSonosController(soco_ok=soco_ok)
    return create_app(
        spotify_client=StubSpotifyClient(devices=devices),
        art_service=StubArtService(),
        available_themes=DEFAULT_THEMES,
        sonos_controller=sonos,
    ).test_client()


# ── existing tests ────────────────────────────────────────────────────────────

def test_create_app_exposes_status_theme_and_playlist_endpoints() -> None:
    spotify_client = StubSpotifyClient()
    app = create_app(
        spotify_client=spotify_client,
        art_service=StubArtService(),
        available_themes=DEFAULT_THEMES,
        sonos_controller=StubSonosController(soco_ok=False),  # force Spotify Connect path
    )
    client = app.test_client()

    status_response = client.get("/api/status")
    assert status_response.status_code == 200
    status_payload = status_response.get_json()
    assert status_payload["playback"]["device_name"] == "Kitchen"
    assert status_payload["playback"]["track"]["title"] == "Teardrop"

    themes_response = client.get("/api/themes")
    assert themes_response.status_code == 200
    themes_payload = themes_response.get_json()
    assert themes_payload["themes"][0]["name"] == "Impressionism"

    art_response = client.get("/api/art/next?theme=Abstract")
    assert art_response.status_code == 200
    art_payload = art_response.get_json()
    assert art_payload["artwork"]["theme"] == "Abstract"

    playlists_response = client.get("/api/playlists")
    assert playlists_response.status_code == 200
    playlists_payload = playlists_response.get_json()
    assert playlists_payload["playlists"][0]["name"] == "Morning Vibes"

    play_response = client.post(
        "/api/playlists/playlist-1/play",
        json={"device_name": "Kitchen"},
    )
    assert play_response.status_code == 200
    assert spotify_client.playback_requests == [
        {
            "playlist_uri": "spotify:playlist:playlist-1",
            "device_name": "Kitchen",
            "shuffle": True,
        }
    ]


def test_index_renders_interactive_controls() -> None:
    app = create_app(
        spotify_client=StubSpotifyClient(),
        art_service=StubArtService(),
        available_themes=DEFAULT_THEMES,
    )
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'id="browse-button"' in html
    assert 'id="playlist-panel"' in html
    assert 'data-theme="Impressionism"' in html
    assert 'src="/static/app.js"' in html


# ── new: device listing ───────────────────────────────────────────────────────

def test_api_devices_returns_available_spotify_devices() -> None:
    client = _make_client(devices=[
        {"id": "device-1", "name": "Kitchen", "type": "Speaker"},
        {"id": "device-2", "name": "Living Room", "type": "Speaker"},
    ])
    response = client.get("/api/devices")
    assert response.status_code == 200
    payload = response.get_json()
    names = [d["name"] for d in payload["devices"]]
    assert "Kitchen" in names
    assert "Living Room" in names


def test_api_devices_returns_empty_list_when_none_available() -> None:
    client = _make_client(devices=[])
    response = client.get("/api/devices")
    assert response.status_code == 200
    assert response.get_json()["devices"] == []


# ── new: no-device error handling ─────────────────────────────────────────────

def test_playlist_play_returns_409_when_no_devices_available() -> None:
    client = _make_client(devices=[])
    response = client.post(
        "/api/playlists/playlist-1/play",
        json={"device_name": "Kitchen"},
    )
    assert response.status_code == 409
    payload = response.get_json()
    assert "no_device" in payload["code"]
    assert "device" in payload["error"].lower()


# ── SoCo-first playback ───────────────────────────────────────────────────────

def _make_client_with_sonos(soco_ok: bool = True, devices=None):
    sonos = StubSonosController(soco_ok=soco_ok)
    spotify = StubSpotifyClient(devices=devices or [])
    app = create_app(
        spotify_client=spotify,
        art_service=StubArtService(),
        available_themes=DEFAULT_THEMES,
        sonos_controller=sonos,
        sonos_room="Kitchen",
    )
    return app.test_client(), sonos, spotify


def test_playlist_play_uses_sonos_soco_when_available() -> None:
    client, sonos, spotify = _make_client_with_sonos(soco_ok=True)
    response = client.post("/api/playlists/playlist-1/play")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["method"] == "sonos"
    assert sonos.play_calls[0]["uri"] == "spotify:playlist:playlist-1"
    assert sonos.play_calls[0]["room_name"] == "Kitchen"
    # Spotify Connect should NOT have been called
    assert spotify.playback_requests == []


def test_playlist_play_falls_back_to_spotify_connect_when_sonos_fails() -> None:
    """When SoCo can't reach the zone, fall back to Spotify Connect."""
    client, sonos, spotify = _make_client_with_sonos(
        soco_ok=False,
        devices=[{"id": "d1", "name": "Kitchen", "type": "Speaker"}],
    )
    response = client.post("/api/playlists/playlist-1/play")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["method"] == "spotify_connect"
    assert len(spotify.playback_requests) == 1


def test_playlist_play_returns_409_when_both_sonos_and_spotify_unavailable() -> None:
    """SoCo fails AND no Spotify devices → 409."""
    client, sonos, spotify = _make_client_with_sonos(soco_ok=False, devices=[])
    response = client.post("/api/playlists/playlist-1/play")
    assert response.status_code == 409
    assert response.get_json()["code"] == "no_device"

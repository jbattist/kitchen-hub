from ui.app import create_app
from art.themes import DEFAULT_THEMES


class StubSpotifyClient:
    def __init__(self) -> None:
        self.playback_requests = []

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

    def start_playlist_playback(self, playlist_uri: str, device_name: str | None = None):
        self.playback_requests.append(
            {"playlist_uri": playlist_uri, "device_name": device_name, "shuffle": True}
        )
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


def test_create_app_exposes_status_theme_and_playlist_endpoints() -> None:
    spotify_client = StubSpotifyClient()
    app = create_app(
        spotify_client=spotify_client,
        art_service=StubArtService(),
        available_themes=DEFAULT_THEMES,
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

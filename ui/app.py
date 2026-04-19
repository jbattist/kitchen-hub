from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request
from spotipy.exceptions import SpotifyException

from art.fetcher import ArtService
from art.themes import DEFAULT_THEMES, ThemeDefinition
from sonos.controller import SonosController


class NullSonosController:
    def pause(self, room_name: str) -> dict:
        return {"ok": True}

    def resume(self, room_name: str) -> dict:
        return {"ok": True}

    def next_track(self, room_name: str) -> dict:
        return {"ok": True}

    def prev_track(self, room_name: str) -> dict:
        return {"ok": True}


class NullSpotifyClient:
    def current_playback(self) -> dict[str, Any]:
        return {
            "is_playing": False,
            "device_name": None,
            "track": None,
        }

    def current_user_playlists(self) -> list[dict[str, Any]]:
        return []

    def pause(self) -> dict[str, Any]:
        return {"ok": True}

    def resume(self) -> dict[str, Any]:
        return {"ok": True}

    def next_track(self) -> dict[str, Any]:
        return {"ok": True}

    def prev_track(self) -> dict[str, Any]:
        return {"ok": True}

    def start_playlist_playback(self, playlist_uri: str, device_name: str | None = None) -> dict[str, bool]:
        return {"ok": bool(playlist_uri), "device_name": device_name}


def create_app(
    spotify_client: Any | None = None,
    art_service: ArtService | None = None,
    available_themes: Sequence[ThemeDefinition] | None = None,
    sonos_controller: Any | None = None,
    sonos_room: str = "Kitchen",
) -> Flask:
    template_folder = str(Path(__file__).with_name("templates"))
    static_folder = str(Path(__file__).with_name("static"))
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)

    spotify_client = spotify_client or NullSpotifyClient()
    art_service = art_service or ArtService()
    available_themes = tuple(available_themes or DEFAULT_THEMES)
    sonos_controller = sonos_controller or NullSonosController()

    @app.get("/")
    def index() -> str:
        return render_template("index.html", themes=available_themes)

    @app.get("/api/status")
    def api_status():
        return jsonify({"playback": spotify_client.current_playback()})

    @app.get("/api/themes")
    def api_themes():
        return jsonify({"themes": [theme.to_dict() for theme in available_themes]})

    @app.get("/api/playlists")
    def api_playlists():
        return jsonify({"playlists": spotify_client.current_user_playlists()})

    @app.post("/api/playlists/<playlist_id>/play")
    def api_playlist_play(playlist_id: str):
        payload = request.get_json(silent=True) or {}
        matching_playlist = next(
            (
                playlist
                for playlist in spotify_client.current_user_playlists()
                if playlist.get("id") == playlist_id
            ),
            None,
        )
        if matching_playlist is None:
            return jsonify({"error": "Playlist not found"}), 404

        try:
            result = spotify_client.start_playlist_playback(
                playlist_uri=matching_playlist["uri"],
                device_name=payload.get("device_name"),
            )
        except SpotifyException as e:
            return jsonify({"error": str(e)}), 502
        return jsonify({"result": result, "playlist": matching_playlist})

    @app.post("/api/playback/pause")
    def api_playback_pause():
        return jsonify(sonos_controller.pause(sonos_room))

    @app.post("/api/playback/resume")
    def api_playback_resume():
        return jsonify(sonos_controller.resume(sonos_room))

    @app.post("/api/playback/next")
    def api_playback_next():
        result = sonos_controller.next_track(sonos_room)
        if result.get("restricted"):
            try:
                return jsonify(spotify_client.next_track())
            except SpotifyException as e:
                return jsonify({"error": str(e)}), 502
        return jsonify(result)

    @app.post("/api/playback/prev")
    def api_playback_prev():
        result = sonos_controller.prev_track(sonos_room)
        if result.get("restricted"):
            try:
                return jsonify(spotify_client.prev_track())
            except SpotifyException as e:
                return jsonify({"error": str(e)}), 502
        return jsonify(result)

    @app.get("/api/art/next")
    def api_art_next():
        theme_name = request.args.get("theme")
        return jsonify({"artwork": art_service.get_next_artwork(theme_name=theme_name)})

    return app

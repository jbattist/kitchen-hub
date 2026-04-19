from __future__ import annotations

from typing import Any

import soco
from soco.exceptions import SoCoUPnPException
from soco.plugins.sharelink import ShareLinkPlugin


class SonosPlaybackError(Exception):
    """Raised when Sonos playback cannot be started."""


class SonosController:
    def discover_room_names(self) -> list[str]:
        zones = soco.discover() or set()
        return sorted(zone.player_name for zone in zones)

    def get_zone(self, room_name: str) -> Any | None:
        zones = soco.discover() or set()
        return next((z for z in zones if z.player_name == room_name), None)

    def pause(self, room_name: str) -> dict[str, Any]:
        zone = self.get_zone(room_name)
        if zone is None:
            return {"ok": False, "error": f"Zone '{room_name}' not found"}
        zone.pause()
        return {"ok": True}

    def resume(self, room_name: str) -> dict[str, Any]:
        zone = self.get_zone(room_name)
        if zone is None:
            return {"ok": False, "error": f"Zone '{room_name}' not found"}
        zone.play()
        return {"ok": True}

    def next_track(self, room_name: str) -> dict[str, Any]:
        zone = self.get_zone(room_name)
        if zone is None:
            return {"ok": False, "error": f"Zone '{room_name}' not found"}
        try:
            zone.next()
        except SoCoUPnPException:
            return {"ok": False, "restricted": True}
        return {"ok": True}

    def prev_track(self, room_name: str) -> dict[str, Any]:
        zone = self.get_zone(room_name)
        if zone is None:
            return {"ok": False, "error": f"Zone '{room_name}' not found"}
        try:
            zone.previous()
        except SoCoUPnPException:
            return {"ok": False, "restricted": True}
        return {"ok": True}

    def set_volume(self, zone: Any, volume: int) -> None:
        zone.volume = volume

    def play_spotify_uri(self, uri: str, room_name: str) -> dict[str, Any]:
        """Play a Spotify URI (playlist, album, track) on a Sonos zone directly via SoCo.

        This bypasses Spotify Connect entirely — no active Spotify session needed.
        Uses SoCo's ShareLinkPlugin to enqueue the Spotify URI.

        Args:
            uri: Spotify URI, e.g. ``spotify:playlist:abc123``.
            room_name: Name of the Sonos zone to play on.

        Returns:
            ``{"ok": True}`` on success, ``{"ok": False, "error": "..."}`` on failure.
        """
        zone = self.get_zone(room_name)
        if zone is None:
            return {"ok": False, "error": f"Zone '{room_name}' not found"}

        try:
            plugin = ShareLinkPlugin(zone)
            zone.clear_queue()
            plugin.add_share_link_to_queue(uri)
            zone.play_from_queue(0)
            return {"ok": True}
        except SoCoUPnPException as exc:
            return {"ok": False, "error": f"Sonos UPnP error: {exc}"}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

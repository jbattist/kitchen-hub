from __future__ import annotations

from typing import Any

import soco
from soco.exceptions import SoCoUPnPException


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

from __future__ import annotations

from typing import Any

import soco


class SonosController:
    def discover_room_names(self) -> list[str]:
        zones = soco.discover() or set()
        return sorted(zone.player_name for zone in zones)

    def set_volume(self, zone: Any, volume: int) -> None:
        zone.volume = volume

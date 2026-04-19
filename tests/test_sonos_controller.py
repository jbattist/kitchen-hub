"""Tests for SonosController.play_spotify_uri using SoCo directly."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from sonos.controller import SonosController, SonosPlaybackError


class TestPlaySpotifyUri:
    def _make_zone(self, name: str = "Kitchen") -> MagicMock:
        zone = MagicMock()
        zone.player_name = name
        return zone

    def _make_controller_with_zone(self, zone: MagicMock) -> SonosController:
        ctrl = SonosController()
        with patch("soco.discover", return_value={zone}):
            # pre-warm; actual calls will also patch
            pass
        return ctrl

    def test_play_spotify_uri_clears_queue_and_plays(self):
        zone = self._make_zone("Kitchen")
        plugin = MagicMock()
        ctrl = SonosController()

        with patch("soco.discover", return_value={zone}), \
             patch("sonos.controller.ShareLinkPlugin", return_value=plugin):
            result = ctrl.play_spotify_uri(
                uri="spotify:playlist:abc123",
                room_name="Kitchen",
            )

        zone.clear_queue.assert_called_once()
        plugin.add_share_link_to_queue.assert_called_once_with("spotify:playlist:abc123")
        zone.play_from_queue.assert_called_once_with(0)
        assert result["ok"] is True

    def test_play_spotify_uri_returns_error_when_zone_not_found(self):
        zone = self._make_zone("Living Room")
        ctrl = SonosController()

        with patch("soco.discover", return_value={zone}):
            result = ctrl.play_spotify_uri(
                uri="spotify:playlist:abc123",
                room_name="Kitchen",
            )

        assert result["ok"] is False
        assert "Kitchen" in result["error"]

    def test_play_spotify_uri_raises_on_soco_exception(self):
        from soco.exceptions import SoCoUPnPException

        zone = self._make_zone("Kitchen")
        plugin = MagicMock()
        plugin.add_share_link_to_queue.side_effect = SoCoUPnPException(
            message="UPnP error", error_code="800", error_xml="<e/>"
        )
        ctrl = SonosController()

        with patch("soco.discover", return_value={zone}), \
             patch("sonos.controller.ShareLinkPlugin", return_value=plugin):
            result = ctrl.play_spotify_uri(
                uri="spotify:playlist:abc123",
                room_name="Kitchen",
            )

        assert result["ok"] is False
        assert "error" in result

from __future__ import annotations

from dataclasses import replace

from art.models import Artwork


class MetMuseumClient:
    @staticmethod
    def normalize_object(payload: dict) -> Artwork:
        return Artwork(
            id=f"met-{payload['objectID']}",
            title=payload.get("title", "Untitled"),
            artist=payload.get("artistDisplayName") or "Unknown artist",
            museum=payload.get("repository") or "The Metropolitan Museum of Art",
            year=payload.get("objectDate") or "Unknown year",
            image_url=payload.get("primaryImage") or "",
        )


class AICClient:
    @staticmethod
    def normalize_artwork(payload: dict) -> Artwork:
        image_id = payload.get("image_id", "")
        return Artwork(
            id=f"aic-{payload['id']}",
            title=payload.get("title", "Untitled"),
            artist=payload.get("artist_display") or "Unknown artist",
            museum="The Art Institute of Chicago",
            year=payload.get("date_display") or "Unknown year",
            image_url=f"https://www.artic.edu/iiif/2/{image_id}/full/843,/0/default.jpg" if image_id else "",
        )


class ClevelandMuseumClient:
    @staticmethod
    def normalize_artwork(payload: dict) -> Artwork:
        creators = payload.get("creators") or []
        first_creator = creators[0]["description"] if creators else "Unknown artist"
        return Artwork(
            id=f"cleveland-{payload['id']}",
            title=payload.get("title", "Untitled"),
            artist=first_creator,
            museum="Cleveland Museum of Art",
            year=payload.get("creation_date") or "Unknown year",
            image_url=((payload.get("images") or {}).get("web") or {}).get("url", ""),
        )


class ArtService:
    def __init__(self, seed_artwork: Artwork | None = None) -> None:
        self._seed_artwork = seed_artwork or Artwork(
            id="seed-1",
            title="Water Lilies",
            artist="Claude Monet",
            museum="The Metropolitan Museum of Art",
            year="1906",
            image_url="https://images.metmuseum.org/CRDImages/ep/original/DT1567.jpg",
            theme="Impressionism",
        )

    def get_next_artwork(self, theme_name: str | None = None) -> dict[str, str | None]:
        artwork = self._seed_artwork
        if theme_name:
            artwork = replace(artwork, theme=theme_name)
        return artwork.to_dict()

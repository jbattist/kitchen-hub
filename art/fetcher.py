from __future__ import annotations

import json
import logging
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path
from typing import Any
from urllib.request import urlopen
from urllib.parse import urlencode
from urllib.error import URLError

from art.models import Artwork
from art.themes import DEFAULT_THEMES, ThemeDefinition

log = logging.getLogger(__name__)

_SEED_ARTWORK = Artwork(
    id="seed-1",
    title="Water Lilies",
    artist="Claude Monet",
    museum="The Metropolitan Museum of Art",
    year="1906",
    image_url="https://images.metmuseum.org/CRDImages/ep/original/DT1567.jpg",
    theme="Impressionism",
)

_THEMES_BY_NAME: dict[str, ThemeDefinition] = {t.name: t for t in DEFAULT_THEMES}


def _http_get_json(url: str) -> dict[str, Any]:
    """Minimal HTTP GET → parsed JSON (no third-party deps)."""
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "KitchenHub/1.0 (museum art display)"})
    with urlopen(req, timeout=10) as resp:  # noqa: S310
        return json.loads(resp.read().decode())


class MetMuseumClient:
    BASE = "https://collectionapi.metmuseum.org/public/collection/v1"

    def _get_json(self, url: str) -> dict[str, Any]:
        return _http_get_json(url)

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

    def search(self, query: str, limit: int = 50) -> list[Artwork]:
        params = urlencode({"q": query, "hasImages": "true", "isPublicDomain": "true"})
        url = f"{self.BASE}/search?{params}"
        try:
            data = self._get_json(url)
        except (URLError, OSError, ValueError) as exc:
            log.warning("Met search failed for %r: %s", query, exc)
            return []

        object_ids = (data.get("objectIDs") or [])[:limit * 2]  # fetch extra to account for filtered
        if not object_ids:
            return []

        artworks: list[Artwork] = []

        def _fetch(oid: int) -> Artwork | None:
            try:
                obj = self._get_json(f"{self.BASE}/objects/{oid}")
                if obj.get("primaryImage"):
                    return self.normalize_object(obj)
            except Exception as exc:  # noqa: BLE001
                log.debug("Met object %d failed: %s", oid, exc)
            return None

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(_fetch, oid): oid for oid in object_ids}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    artworks.append(result)
                if len(artworks) >= limit:
                    break

        return artworks


class AICClient:
    BASE = "https://api.artic.edu/api/v1"
    FIELDS = "id,title,artist_display,date_display,image_id,is_public_domain"

    def _get_json(self, url: str) -> dict[str, Any]:
        return _http_get_json(url)

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

    def search(self, query: str, limit: int = 50) -> list[Artwork]:
        params = urlencode({
            "q": query,
            "fields": self.FIELDS,
            "limit": min(limit, 100),
            "query[term][is_public_domain]": "true",
        })
        url = f"{self.BASE}/artworks/search?{params}"
        try:
            data = self._get_json(url)
        except (URLError, OSError, ValueError) as exc:
            log.warning("AIC search failed for %r: %s", query, exc)
            return []

        artworks = []
        for item in data.get("data") or []:
            if item.get("image_id") and item.get("is_public_domain"):
                artworks.append(self.normalize_artwork(item))
        return artworks


class ClevelandMuseumClient:
    BASE = "https://openaccess-api.clevelandart.org/api"

    def _get_json(self, url: str) -> dict[str, Any]:
        return _http_get_json(url)

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

    def search(self, query: str, limit: int = 50) -> list[Artwork]:
        params = urlencode({"q": query, "has_image": 1, "cc0": 1, "limit": limit, "type": "Painting"})
        url = f"{self.BASE}/artworks/?{params}"
        try:
            data = self._get_json(url)
        except (URLError, OSError, ValueError) as exc:
            log.warning("Cleveland search failed for %r: %s", query, exc)
            return []

        artworks = []
        for item in data.get("data") or []:
            url_img = ((item.get("images") or {}).get("web") or {}).get("url", "")
            if url_img:
                artworks.append(self.normalize_artwork(item))
        return artworks


class ArtService:
    """Manages a shuffled pool of artworks per theme, fetching from real museum APIs."""

    def __init__(
        self,
        cache_dir: str | Path | None = None,
        default_theme: str = "Impressionism",
    ) -> None:
        self._cache_dir = Path(cache_dir).expanduser() if cache_dir else None
        self._default_theme = default_theme
        self._pools: dict[str, list[Artwork]] = {}  # theme → shuffled pool
        self._met = MetMuseumClient()
        self._aic = AICClient()
        self._cleveland = ClevelandMuseumClient()

    # ── public ──────────────────────────────────────────────────────────────

    def get_next_artwork(self, theme_name: str | None = None) -> dict[str, str | None]:
        name = theme_name or self._default_theme
        pool = self._pools.get(name)

        if not pool:
            pool = self._fetch_for_theme(name)
            if pool:
                random.shuffle(pool)
            self._pools[name] = pool

        if not pool:
            log.warning("No artwork fetched for theme %r — using seed", name)
            return replace(_SEED_ARTWORK, theme=name).to_dict()

        artwork = pool.pop(0)
        if not pool:
            # Exhausted — clear so next call refetches
            del self._pools[name]

        return replace(artwork, theme=name).to_dict()

    # ── internal ────────────────────────────────────────────────────────────

    def _fetch_for_theme(self, theme_name: str) -> list[Artwork]:
        """Fetch a batch of artworks for a theme from all configured museum APIs."""
        theme = _THEMES_BY_NAME.get(theme_name)
        if theme is None:
            return []

        results: list[Artwork] = []
        museums = set(theme.museums)

        for term in theme.query_terms:
            if "Met" in museums:
                results.extend(self._met.search(term, limit=20))
            if "AIC" in museums:
                results.extend(self._aic.search(term, limit=20))
            if "Cleveland" in museums:
                results.extend(self._cleveland.search(term, limit=20))

        # Deduplicate by id
        seen: set[str] = set()
        unique: list[Artwork] = []
        for art in results:
            if art.id not in seen and art.image_url:
                seen.add(art.id)
                unique.append(art)

        if self._cache_dir and unique:
            self._persist(unique, theme_name)

        return unique

    def _persist(self, artworks: list[Artwork], theme_name: str) -> None:
        try:
            theme_dir = self._cache_dir / theme_name.replace(" ", "_")  # type: ignore[operator]
            theme_dir.mkdir(parents=True, exist_ok=True)
            for art in artworks:
                (theme_dir / f"{art.id}.json").write_text(
                    json.dumps(art.to_dict(), indent=2), encoding="utf-8"
                )
        except OSError as exc:
            log.warning("Failed to persist artwork cache: %s", exc)

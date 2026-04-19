"""Tests for museum API clients and ArtService pool management."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from art.fetcher import AICClient, ArtService, ClevelandMuseumClient, MetMuseumClient
from art.models import Artwork
from art.themes import DEFAULT_THEMES


# ── Normalization (unchanged) ─────────────────────────────────────────────────

def test_met_client_extracts_public_domain_artwork() -> None:
    payload = {
        "objectID": 42,
        "title": "Water Lilies",
        "artistDisplayName": "Claude Monet",
        "objectDate": "1906",
        "primaryImage": "https://images.metmuseum.org/42.jpg",
        "isPublicDomain": True,
        "repository": "The Metropolitan Museum of Art",
    }

    artwork = MetMuseumClient.normalize_object(payload)

    assert artwork.id == "met-42"
    assert artwork.title == "Water Lilies"
    assert artwork.artist == "Claude Monet"
    assert artwork.image_url == "https://images.metmuseum.org/42.jpg"
    assert artwork.museum == "The Metropolitan Museum of Art"


def test_aic_client_builds_iiif_url() -> None:
    payload = {
        "id": 7,
        "title": "The Bedroom",
        "artist_display": "Vincent van Gogh",
        "date_display": "1889",
        "image_id": "abc123",
    }

    artwork = AICClient.normalize_artwork(payload)

    assert artwork.id == "aic-7"
    assert artwork.image_url == "https://www.artic.edu/iiif/2/abc123/full/843,/0/default.jpg"


def test_cleveland_client_uses_web_image_url() -> None:
    payload = {
        "id": 9,
        "title": "Composition",
        "creators": [{"description": "Wassily Kandinsky"}],
        "creation_date": "1913",
        "images": {"web": {"url": "https://clevelandart.org/9.jpg"}},
        "department": "Modern Art",
    }

    artwork = ClevelandMuseumClient.normalize_artwork(payload)

    assert artwork.id == "cleveland-9"
    assert artwork.artist == "Wassily Kandinsky"
    assert artwork.image_url == "https://clevelandart.org/9.jpg"


# ── MetMuseumClient.search ────────────────────────────────────────────────────

def test_met_client_search_returns_artworks() -> None:
    search_response = {"objectIDs": [1, 2]}
    obj1 = {
        "objectID": 1, "title": "Starry Night", "artistDisplayName": "Van Gogh",
        "objectDate": "1889", "primaryImage": "https://example.com/1.jpg",
        "isPublicDomain": True, "repository": "Met",
    }
    obj2 = {
        "objectID": 2, "title": "Irises", "artistDisplayName": "Van Gogh",
        "objectDate": "1890", "primaryImage": "https://example.com/2.jpg",
        "isPublicDomain": True, "repository": "Met",
    }

    client = MetMuseumClient()
    with patch.object(client, "_get_json") as mock_get:
        mock_get.side_effect = [search_response, obj1, obj2]
        results = client.search("van gogh", limit=10)

    assert len(results) == 2
    assert results[0].id == "met-1"
    assert results[1].id == "met-2"


def test_met_client_search_skips_objects_without_images() -> None:
    search_response = {"objectIDs": [1, 2]}
    obj1 = {
        "objectID": 1, "title": "Painting", "artistDisplayName": "Artist",
        "objectDate": "1900", "primaryImage": "",  # no image
        "isPublicDomain": True, "repository": "Met",
    }
    obj2 = {
        "objectID": 2, "title": "Sculpture", "artistDisplayName": "Artist",
        "objectDate": "1900", "primaryImage": "https://example.com/2.jpg",
        "isPublicDomain": True, "repository": "Met",
    }

    client = MetMuseumClient()
    with patch.object(client, "_get_json") as mock_get:
        mock_get.side_effect = [search_response, obj1, obj2]
        results = client.search("art", limit=10)

    assert len(results) == 1
    assert results[0].id == "met-2"


# ── AICClient.search ──────────────────────────────────────────────────────────

def test_aic_client_search_returns_artworks() -> None:
    api_response = {
        "data": [
            {"id": 10, "title": "The Bath", "artist_display": "Mary Cassatt",
             "date_display": "1892", "image_id": "img-abc", "is_public_domain": True},
            {"id": 11, "title": "Nude", "artist_display": "Renoir",
             "date_display": "1880", "image_id": None, "is_public_domain": True},  # no image
        ]
    }

    client = AICClient()
    with patch.object(client, "_get_json", return_value=api_response):
        results = client.search("impressionism", limit=10)

    assert len(results) == 1
    assert results[0].id == "aic-10"
    assert "img-abc" in results[0].image_url


# ── ClevelandMuseumClient.search ──────────────────────────────────────────────

def test_cleveland_client_search_returns_artworks() -> None:
    api_response = {
        "data": [
            {
                "id": 99, "title": "Abstract Form", "creation_date": "1913",
                "creators": [{"description": "Kandinsky"}],
                "images": {"web": {"url": "https://clevelandart.org/99.jpg"}},
            }
        ]
    }

    client = ClevelandMuseumClient()
    with patch.object(client, "_get_json", return_value=api_response):
        results = client.search("abstract", limit=10)

    assert len(results) == 1
    assert results[0].id == "cleveland-99"


# ── ArtService pool management ────────────────────────────────────────────────

def _make_artwork(n: int, theme: str = "Impressionism") -> Artwork:
    return Artwork(
        id=f"met-{n}", title=f"Painting {n}", artist="Artist",
        museum="Met", year="1900",
        image_url=f"https://example.com/{n}.jpg", theme=theme,
    )


def test_art_service_fills_pool_from_apis_on_first_request(tmp_path) -> None:
    artworks = [_make_artwork(i) for i in range(5)]
    theme = DEFAULT_THEMES[0]  # Impressionism

    service = ArtService(cache_dir=tmp_path)

    with patch.object(service, "_fetch_for_theme", return_value=artworks) as mock_fetch:
        result = service.get_next_artwork(theme_name=theme.name)

    mock_fetch.assert_called_once_with(theme.name)
    assert result["image_url"].startswith("https://example.com/")


def test_art_service_cycles_through_pool_without_refetching(tmp_path) -> None:
    artworks = [_make_artwork(i) for i in range(3)]

    service = ArtService(cache_dir=tmp_path)

    with patch.object(service, "_fetch_for_theme", return_value=artworks) as mock_fetch:
        for _ in range(3):
            service.get_next_artwork(theme_name="Impressionism")

    # Pool was filled once and cycled through — should not have refetched
    assert mock_fetch.call_count == 1


def test_art_service_refills_pool_when_exhausted(tmp_path) -> None:
    artworks = [_make_artwork(i) for i in range(2)]

    service = ArtService(cache_dir=tmp_path)

    with patch.object(service, "_fetch_for_theme", return_value=artworks) as mock_fetch:
        for _ in range(5):
            service.get_next_artwork(theme_name="Impressionism")

    # Should have refilled at least twice (pool of 2, called 5 times)
    assert mock_fetch.call_count >= 2


def test_art_service_returns_seed_artwork_when_api_fails(tmp_path) -> None:
    service = ArtService(cache_dir=tmp_path)

    with patch.object(service, "_fetch_for_theme", return_value=[]):
        result = service.get_next_artwork(theme_name="Impressionism")

    assert result["title"] is not None  # seed artwork returned


def test_art_service_uses_default_theme_when_none_specified(tmp_path) -> None:
    artworks = [_make_artwork(i) for i in range(3)]
    service = ArtService(cache_dir=tmp_path)

    with patch.object(service, "_fetch_for_theme", return_value=artworks):
        result = service.get_next_artwork(theme_name=None)

    assert result is not None

from art.fetcher import AICClient, ClevelandMuseumClient, MetMuseumClient


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

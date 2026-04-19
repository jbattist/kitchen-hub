from __future__ import annotations

from app_config import load_config
from art.fetcher import ArtService
from ui.app import create_app


def main() -> None:
    settings = load_config()
    app = create_app(art_service=ArtService())
    app.run(host="0.0.0.0", port=5000, debug=False)


if __name__ == "__main__":
    main()

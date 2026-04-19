from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ThemeDefinition:
    name: str
    query_terms: tuple[str, ...]
    museums: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


DEFAULT_THEMES: tuple[ThemeDefinition, ...] = (
    ThemeDefinition(
        name="Impressionism",
        query_terms=("impressionism", "monet", "renoir", "degas"),
        museums=("Met", "AIC", "Rijksmuseum"),
    ),
    ThemeDefinition(
        name="Abstract",
        query_terms=("abstract", "kandinsky", "mondrian", "rothko"),
        museums=("Met", "AIC", "Cleveland"),
    ),
    ThemeDefinition(
        name="Dutch Masters",
        query_terms=("rembrandt", "vermeer", "dutch golden age"),
        museums=("Rijksmuseum", "Met"),
    ),
    ThemeDefinition(
        name="Modernism",
        query_terms=("modernism", "picasso", "matisse", "cezanne"),
        museums=("Met", "AIC"),
    ),
    ThemeDefinition(
        name="Landscapes",
        query_terms=("landscape", "nature", "plein air"),
        museums=("Met", "AIC", "Cleveland"),
    ),
    ThemeDefinition(
        name="Portraits",
        query_terms=("portrait",),
        museums=("Met", "AIC", "Cleveland", "Rijksmuseum"),
    ),
)


def list_theme_dicts() -> list[dict[str, object]]:
    return [theme.to_dict() for theme in DEFAULT_THEMES]

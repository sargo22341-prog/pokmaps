"""Le catalogue de provenance couvre toutes les espèces épinglées et reste reproductible."""

from pathlib import Path

from pokemaps_data.builder import DatabaseBuilder
from pokemaps_data.sprite_catalog import sprite_catalog


def test_complete_catalog(builder: DatabaseBuilder) -> None:
    content = sprite_catalog(builder.api)
    assert "| 1 | Bulbizarre | 1 |" in content
    assert "| 1025 | Pêchaminus | 9 |" in content
    assert "| 650 | Marisson | 6 | Non configuré" in content
    assert len([line for line in content.splitlines() if line.startswith("| ") and line[2].isdigit()]) == 1025
    document = Path(__file__).resolve().parents[2] / "docs/donnees/sprites-pokemon.md"
    assert document.read_text("utf-8") == content

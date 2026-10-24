"""Translations des points éditoriaux vers les plans distribués de Sinnoh et HGSS."""

from pathlib import Path

from .maps_assembly_coordinates_gen4 import editor_offsets as sinnoh_offsets
from .maps_layout import identifier
from .placement_hgss import read_placement_json


def editor_offsets(maps: Path) -> dict[tuple[str, str], tuple[int, int]]:
    result = sinnoh_offsets(maps)
    path = maps / "heartgold-soulsilver/assemblies.json"
    if not path.is_file():
        return result
    rows = read_placement_json(path)
    if len(rows) != 496:
        raise ValueError("HGSS : repères natifs distribués incomplets")
    for const, row in rows.items():
        offset = row["offset"]
        # Retirer la marge transparente d'un habitat peut déplacer son origine avant le bord du plan.
        if len(offset) != 2 or any(type(n) is not int or not -32768 <= n <= 32768 for n in offset):
            raise ValueError(f"HGSS : translation native invalide : {const}")
        result[("heartgold-soulsilver", identifier(const))] = tuple(offset)
    return result

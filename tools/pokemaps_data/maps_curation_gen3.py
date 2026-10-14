"""Curations GBA des layouts affichés : layout choisi par un script et bande de remplissage retirée.

- map_layouts.csv : le layout qu'un script de la carte lui donne (`setmaplayoutindex`) quand c'est lui qui
  contient tous ses événements (le tunnel creusé de l'Île 3, où se trouvent le prospecteur et la Pépite cachée).
- map_trims.csv : largeur et hauteur affichées d'une carte dont le layout est complété à droite ou en bas par une
  seule métatuile de remplissage, sans case ni événement du jeu (rez-de-chaussée de la Route Victoire des remakes).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, replace

from .pret_gen3 import Gen3PretRepo
from .pret_gen3_maps import Gen3Map, script_layouts
from .pret_gen3_source import read_json
from .sources import DATA_DIR


@dataclass(frozen=True)
class LayoutChoice:
    family: str
    map: str
    layout: str


@dataclass(frozen=True)
class MapTrim:
    family: str
    map: str
    width: int  # en métatuiles
    height: int


def read_layout_choices() -> tuple[LayoutChoice, ...]:
    with (DATA_DIR / "map_layouts.csv").open(encoding="utf-8", newline="") as handle:
        return tuple(LayoutChoice(row["family"], row["map"], row["layout"]) for row in csv.DictReader(handle))


def read_trims() -> tuple[MapTrim, ...]:
    with (DATA_DIR / "map_trims.csv").open(encoding="utf-8", newline="") as handle:
        return tuple(
            MapTrim(row["family"], row["map"], int(row["width"]), int(row["height"])) for row in csv.DictReader(handle)
        )


def choose_layouts(maps: dict[str, Gen3Map], repo: Gen3PretRepo, choices: list[LayoutChoice]) -> None:
    """Remplace le layout des cartes choisies, après avoir vérifié qu'un de leurs scripts le sélectionne."""
    rows = read_json(repo.root / "data/layouts/layouts.json")["layouts"]
    for choice in choices:
        current = maps.get(choice.map)
        if current is None or choice.layout not in repo.layouts:
            raise ValueError(f"map_layouts.csv : carte ou layout inconnu : {choice}")
        if choice.layout not in script_layouts(repo.root, rows, current.shared_scripts_map or current.label):
            raise ValueError(f"map_layouts.csv : aucun script de {choice.map} ne sélectionne {choice.layout}")
        layout = repo.layouts[choice.layout]
        if (layout.width, layout.height) != (current.width, current.height):
            raise ValueError(f"map_layouts.csv : dimensions différentes pour {choice.map}")
        maps[choice.map] = replace(current, layout=layout)


def trim_maps(maps: dict[str, Gen3Map], trims: list[MapTrim]) -> None:
    """Retire la bande droite ou basse d'une seule métatuile, qui ne contient aucun événement de la carte."""
    for trim in trims:
        current = maps.get(trim.map)
        if current is None:
            raise ValueError(f"map_trims.csv : carte inconnue : {trim}")
        if not (0 < trim.width <= current.width and 0 < trim.height <= current.height) or (
            trim.width == current.width and trim.height == current.height
        ):
            raise ValueError(f"map_trims.csv : dimensions qui ne réduisent pas la carte : {trim}")
        removed = [
            (x, y) for y in range(current.height) for x in range(current.width) if x >= trim.width or y >= trim.height
        ]
        if len({current.block(x, y) for x, y in removed}) != 1:
            raise ValueError(f"map_trims.csv : bande retirée non uniforme : {trim.map}")
        events = (*current.objects, *current.coord_events, *current.bg_events, *current.warps)
        if any(event.x >= trim.width or event.y >= trim.height for event in events):
            raise ValueError(f"map_trims.csv : événement dans la bande retirée : {trim.map}")
        layout = current.layout
        cells = tuple(layout.cells[y * layout.width + x] for y in range(trim.height) for x in range(trim.width))
        trimmed = replace(layout, const=f"{layout.const}_TRIMMED", width=trim.width, height=trim.height, cells=cells)
        maps[trim.map] = replace(current, layout=trimmed)

"""Terrains qui manquent d'emplacements pour leurs Pokémon, sur toutes les cartes de l'éditeur.

Avec moins d'emplacements que de Pokémon, l'application dessine un Pokémon tiré au hasard par emplacement
(WildPlacement.kt) : les autres ne sont visibles que dans la liste du lieu. C'est un avertissement. Sans aucun
emplacement, aucun Pokémon du terrain n'est dessiné : c'est une erreur qui bloque l'enregistrement."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from pokemaps_data.map_spots import SPOT_KINDS, Point, TerrainKey, selected_key

from .catalog import EditorCatalog, Family, required_spots, used_by_app
from .session import SpotSession

_VERSION_LABELS = {"red-blue": "Rouge/Bleu", "yellow": "Jaune", "gold-silver": "Or/Argent", "crystal": "Cristal"}


class TerrainKinds(Protocol):
    def kinds(self, family: Family, map_identifier: str) -> frozenset[str]: ...


@dataclass(frozen=True)
class Shortfall:
    """Terrain d'un lieu, dans un groupe de versions, qui a moins d'emplacements que de Pokémon à dessiner.

    `key` est la portée qui décide de ses emplacements (commune à la famille ou propre au groupe) ; `version_group`
    est le groupe dont le plan montre le manque."""

    key: TerrainKey
    version_group: str
    map_name: str
    points: int
    required: int

    @property
    def blocking(self) -> bool:
        return self.points == 0

    @property
    def message(self) -> str:
        if self.blocking:
            return f"aucun emplacement pour {self.required} Pokémon : aucun ne serait affiché"
        hidden = self.required - self.points
        return f"{self.points} emplacement(s) pour {self.required} Pokémon, {hidden} visible(s) dans la liste seulement"

    @property
    def label(self) -> str:
        version = _VERSION_LABELS.get(self.version_group, self.version_group)
        return f"{self.map_name} · {version} · {self.key.kind} : {self.message}"


@dataclass(frozen=True)
class _PlaceNeeds:
    """Besoins d'un lieu dans un groupe de versions, lus une fois dans la base et les sources pret."""

    family: str
    map_identifier: str
    map_name: str
    version_group: str
    kinds: frozenset[str]
    required: Mapping[str, int]
    generated: Mapping[str, frozenset[Point]]


class PlacementNeeds:
    """Pokémon à dessiner sur chaque terrain de chaque lieu ; le contrôle ne relit ensuite que la session."""

    def __init__(self, catalog: EditorCatalog, families: list[Family], terrains: TerrainKinds) -> None:
        self._places: list[_PlaceNeeds] = []
        for family in families:
            for group in family.version_groups:
                scope = Family(family.identifier, family.label, (group,))
                for found in catalog.maps(scope):
                    lines = catalog.encounters(found)
                    self._places.append(
                        _PlaceNeeds(
                            family.identifier,
                            found.identifier,
                            found.name,
                            group,
                            terrains.kinds(scope, found.identifier),
                            {kind: required_spots(lines, kind) for kind in SPOT_KINDS},
                            catalog.generated_spots(found),
                        )
                    )

    def shortfalls(self, session: SpotSession) -> list[Shortfall]:
        """Un manque par portée d'emplacements, le plus grand quand plusieurs groupes la partagent."""
        merged = session.merged()
        found: dict[TerrainKey, Shortfall] = {}
        for place in self._places:
            for shortfall in _place_shortfalls(place, session, merged):
                known = found.get(shortfall.key)
                if known is None or shortfall.required - shortfall.points > known.required - known.points:
                    found[shortfall.key] = shortfall
        return sorted(found.values(), key=lambda item: (item.key, item.version_group))


def _place_shortfalls(
    place: _PlaceNeeds, session: SpotSession, merged: Mapping[TerrainKey, frozenset[Point]]
) -> list[Shortfall]:
    def key(kind: str) -> TerrainKey:
        common = TerrainKey(place.family, place.map_identifier, kind)
        return selected_key(merged, common, place.version_group)

    counts = {kind: len(session.points(key(kind), place.generated[kind])) for kind in SPOT_KINDS}
    has_grass, has_floor = counts["grass"] > 0, counts["floor"] > 0
    result = []
    for kind in SPOT_KINDS:
        needed = place.required[kind]
        if not needed or counts[kind] >= needed or not _drawn_on(kind, has_grass, has_floor, place.kinds):
            continue
        result.append(Shortfall(key(kind), place.version_group, place.map_name, counts[kind], needed))
    return result


def _drawn_on(kind: str, has_grass: bool, has_floor: bool, possible: frozenset[str]) -> bool:
    """Vrai si l'application dessine sur ce terrain. Sans point ni dans les herbes ni au sol, le manque est signalé
    sur celui des deux où l'on peut en poser (les herbes d'abord)."""
    if kind not in possible:
        return False
    if kind in ("grass", "floor") and not (has_grass or has_floor):
        return kind == "grass" or "grass" not in possible
    return used_by_app(kind, has_grass, has_floor)

"""Lecture de la base générée pour l'éditeur : familles de jeux, lieux, rencontres et emplacements."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, replace
from pathlib import Path

from pokemaps_data.games import map_families
from pokemaps_data.map_spots import SPOT_KINDS, Point
from pokemaps_data.pret import STEP_PX

# Méthode sous laquelle l'application regroupe une rencontre sauvage (ui/map/MapZoneContent.kt) : un même
# Pokémon pêché à l'Ancienne, à la Super ou à la Méga Canne n'a qu'un marqueur, mais un de plus s'il surfe. Coup
# d'Boule réunit de même les arbres ordinaires et les arbres rares (2e génération).
_PLACEMENT_METHODS = {
    "walk": "walk",
    "surf": "surf",
    "old-rod": "fishing",
    "good-rod": "fishing",
    "super-rod": "fishing",
    "headbutt": "headbutt",
    "headbutt-high": "headbutt",
    "rock-smash": "rock-smash",
}
# Terrain sur lequel l'application dessine chaque méthode : la marche utilise les herbes, ou le sol sans herbes.
_TERRAINS = {
    "walk": ("grass", "floor"),
    "surf": ("water",),
    "fishing": ("water",),
    "headbutt": ("tree",),
    "rock-smash": ("rock",),
}
_WILD = tuple(_PLACEMENT_METHODS)
_IN_WILD = f"({', '.join('?' * len(_WILD))})"
CELL_PX = STEP_PX


@dataclass(frozen=True)
class Family:
    """Jeux qui partagent leurs plans, donc leurs emplacements (Rouge, Bleu et Jaune…)."""

    identifier: str
    label: str
    version_groups: tuple[str, ...]


@dataclass(frozen=True)
class EditorMap:
    """Lieu à éditer. Le rectangle (x, y, width, height) est en pixels de la carte affichée `displayed`."""

    family: str
    identifier: str
    name: str
    version_group: str
    map_ids: tuple[int, ...]
    displayed: str
    x: int
    y: int
    width: int
    height: int

    def snap(self, x: float, y: float) -> Point | None:
        """Centre de la case (16 px) sous le point, comme les emplacements générés ; None hors du lieu."""
        column, row = int((x - self.x) // CELL_PX), int((y - self.y) // CELL_PX)
        if not (0 <= column * CELL_PX < self.width and 0 <= row * CELL_PX < self.height):
            return None
        return self.x + column * CELL_PX + CELL_PX // 2, self.y + row * CELL_PX + CELL_PX // 2


@dataclass(frozen=True)
class EncounterLine:
    """Un Pokémon sauvage d'un lieu, pour une version et une méthode, probabilités des créneaux cumulées."""

    version: str
    method: str
    method_name: str
    pokemon_id: int
    pokemon: str
    min_level: int
    max_level: int
    chance: float | None

    @property
    def terrains(self) -> tuple[str, ...]:
        return _TERRAINS[_PLACEMENT_METHODS[self.method]]

    @property
    def label(self) -> str:
        probability = "—" if self.chance is None else f"{self.chance:g} %"
        levels = f"{self.min_level}" if self.min_level == self.max_level else f"{self.min_level}–{self.max_level}"
        return f"{self.version} · {self.method_name} · {self.pokemon} · niv. {levels} · {probability}"


@dataclass(frozen=True)
class MapMark:
    """Objet, personnage ou entrée que l'application dessine sur le lieu, en pixels de la carte affichée.

    `kind` est le genre de map_object (item, trainer, npc…) ou « warp » pour une entrée ; `item` n'est renseigné
    que si l'objet a une icône."""

    kind: str
    x: int
    y: int
    sprite: str | None
    item: str | None
    pokemon_id: int | None


def required_spots(lines: list[EncounterLine], kind: str) -> int:
    """Marqueurs que l'application doit placer sur ce terrain dans la version qui en demande le plus."""
    markers: dict[str, set[tuple[str, int]]] = {}
    for line in lines:
        if kind in line.terrains:
            markers.setdefault(line.version, set()).add((_PLACEMENT_METHODS[line.method], line.pokemon_id))
    return max((len(found) for found in markers.values()), default=0)


def used_by_app(kind: str, has_grass: bool, has_floor: bool) -> bool:
    """Vrai si l'application dessine sur ce terrain : en marchant, elle prend les herbes s'il y en a, sinon le sol."""
    if kind not in ("grass", "floor"):
        return True
    walking = "floor" if has_floor and not has_grass else "grass"
    return kind == walking


class EditorCatalog:
    """Requêtes de l'éditeur sur pokedex.db, ouverte en lecture seule."""

    def __init__(self, database: Path) -> None:
        if not database.is_file():
            raise FileNotFoundError(f"Base absente : lancer d'abord python tools/build_data.py ({database})")
        self.connection = sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)

    def close(self) -> None:
        self.connection.close()

    def families(self) -> list[Family]:
        """Familles de cartes dont au moins un jeu est présent dans la base."""
        names = dict(
            self.connection.execute(
                """SELECT vg.identifier, group_concat(v.name_fr, '|') FROM version_group vg
                   JOIN version v ON v.version_group_id = vg.id GROUP BY vg.id ORDER BY vg.id"""
            )
        )
        result = []
        for family, groups in map_families().items():
            present = tuple(group for group in groups if group in names)
            versions = [name for group in present for name in names[group].split("|")]
            if versions:
                label = versions[0] if len(versions) == 1 else f"{', '.join(versions[:-1])} et {versions[-1]}"
                result.append(Family(family, label, present))
        return result

    def maps(self, family: Family) -> list[EditorMap]:
        """Lieux ayant des rencontres sauvages dans au moins un jeu de la famille, réunis par identifiant."""
        found: dict[str, EditorMap] = {}
        for group in family.version_groups:
            for row in self._wild_maps(group):
                map_id, identifier, name, x, y, width, height, parent = row
                known = found.get(identifier)
                if known is not None:
                    found[identifier] = replace(known, map_ids=(*known.map_ids, map_id))
                    continue
                origin = (x, y) if parent else (0, 0)
                found[identifier] = EditorMap(
                    family.identifier, identifier, name, group, (map_id,), parent or identifier, *origin, width, height
                )
        return sorted(found.values(), key=lambda editor_map: editor_map.name)

    def world_names(self, family: Family) -> dict[str, str]:
        """Cartes du monde des jeux de la famille (une par région) : identifiant -> nom (« johto » -> « Johto »)."""
        groups = family.version_groups
        rows = self.connection.execute(
            f"""SELECT DISTINCT world.identifier, world.name_fr FROM map world
                JOIN version_group vg ON vg.id = world.version_group_id
                WHERE vg.identifier IN ({", ".join("?" * len(groups))})
                  AND world.is_world = 1
                ORDER BY world.id""",
            groups,
        )
        return dict(rows)

    def encounters(self, editor_map: EditorMap) -> list[EncounterLine]:
        ids = editor_map.map_ids
        rows = self.connection.execute(
            f"""SELECT v.name_fr, method.identifier, method.name_fr, pokemon.id, pokemon.name_fr,
                       min(e.min_level), max(e.max_level), sum(e.chance)
                FROM map JOIN map_area area ON area.map_id = map.id
                JOIN encounter e ON e.location_area_id = area.location_area_id
                JOIN encounter_method method ON method.id = e.method_id
                JOIN pokemon ON pokemon.id = e.pokemon_id
                JOIN version v ON v.id = e.version_id AND v.version_group_id = map.version_group_id
                WHERE map.id IN ({", ".join("?" * len(ids))}) AND method.identifier IN {_IN_WILD}
                GROUP BY v.id, method.id, pokemon.id
                ORDER BY v.id, method.sort_order, sum(e.chance) DESC, pokemon.name_fr""",
            (*ids, *_WILD),
        )
        return [EncounterLine(*row) for row in rows]

    def generated_spots(self, editor_map: EditorMap) -> dict[str, frozenset[Point]]:
        """Emplacements de la base, pour le premier jeu de la famille qui contient le lieu."""
        rows = self.connection.execute("SELECT kind, x, y FROM map_spot WHERE map_id = ?", (editor_map.map_ids[0],))
        points: dict[str, set[Point]] = {kind: set() for kind in SPOT_KINDS}
        for kind, x, y in rows:
            points[kind].add((x, y))
        return {kind: frozenset(found) for kind, found in points.items()}

    def marks(self, editor_map: EditorMap) -> list[MapMark]:
        """Objets, personnages et entrées du lieu, pour la première version du premier jeu de la famille qui le
        contient."""
        rows = self.connection.execute(
            """SELECT o.kind, o.x, o.y, o.sprite, CASE WHEN item.has_sprite THEN item.identifier END, o.pokemon_id
               FROM map_object o LEFT JOIN item ON item.id = o.item_id JOIN map m ON m.id = o.map_id
               WHERE o.map_id = :map AND (o.version_id IS NULL OR o.version_id =
                 (SELECT min(v.id) FROM version v WHERE v.version_group_id = m.version_group_id))
               UNION ALL
               SELECT 'warp', x, y, NULL, NULL, NULL FROM map_warp WHERE map_id = :map""",
            {"map": editor_map.map_ids[0]},
        )
        return [MapMark(*row) for row in rows]

    def _wild_maps(self, version_group: str) -> list[tuple]:
        return self.connection.execute(
            f"""SELECT map.id, map.identifier, map.name_fr, map.x, map.y, map.width, map.height, parent.identifier
                FROM map JOIN version_group vg ON vg.id = map.version_group_id
                LEFT JOIN map parent ON parent.id = map.parent_map_id
                WHERE vg.identifier = ? AND EXISTS (
                    SELECT 1 FROM map_area area
                    JOIN encounter e ON e.location_area_id = area.location_area_id
                    JOIN encounter_method method ON method.id = e.method_id
                    JOIN version v ON v.id = e.version_id AND v.version_group_id = map.version_group_id
                    WHERE area.map_id = map.id AND method.identifier IN {_IN_WILD})""",
            (version_group, *_WILD),
        ).fetchall()

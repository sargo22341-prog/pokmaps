"""Lecture des terrains HGSS distribués, sans relancer les lecteurs de sources."""

from pathlib import Path

from pokemaps_data.map_spots import Point
from pokemaps_data.placement_hgss import read_placement_json


class HgssTerrain:
    def __init__(self, maps: Path) -> None:
        self._rows = read_placement_json(maps / "heartgold-soulsilver/terrain.json")
        if len(self._rows) != 496:
            raise ValueError("HGSS : terrains distribués incomplets")

    def kinds(self, name: str) -> frozenset[str]:
        return frozenset(self._rows[name]["terrain"])

    def points(self, name: str, kind: str) -> frozenset[Point]:
        return frozenset(map(tuple, self._rows[name]["terrain"].get(kind, [])))

    def region(self, name: str) -> str | None:
        scope = self._rows[name]["scope"]
        return scope if scope in {"johto", "kanto"} else None

    def snap(self, name: str, kind: str, x: float, y: float) -> Point | None:
        nearest = min(self.points(name, kind), key=lambda p: ((p[0] - x) ** 2 + (p[1] - y) ** 2, p), default=None)
        if nearest is not None and (nearest[0] - x) ** 2 + (nearest[1] - y) ** 2 <= 12**2:
            return nearest
        return None

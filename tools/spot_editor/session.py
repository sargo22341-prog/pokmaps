"""État d'édition : emplacements retouchés, modifications en attente et contrôles avant enregistrement."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from pokemaps_data.map_spots import Point, TerrainKey


class Toggle(Enum):
    """Effet d'un clic sur la carte."""

    ADDED = "added"
    REMOVED = "removed"


@dataclass(frozen=True)
class Shortfall:
    """Terrain qui a moins d'emplacements que de Pokémon à y dessiner."""

    key: TerrainKey
    map_name: str
    points: int
    required: int


class SpotSession:
    """Emplacements affichés : modification en attente, sinon retouche enregistrée, sinon terrain généré.

    Seuls les terrains réellement modifiés sont mis en attente : un terrain qu'on n'a pas touché reste
    généré (il n'est pas recopié dans map_spots.csv)."""

    def __init__(self, curated: dict[TerrainKey, frozenset[Point]]) -> None:
        self.curated = dict(curated)
        self.pending: dict[TerrainKey, frozenset[Point]] = {}

    @property
    def has_changes(self) -> bool:
        return bool(self.pending)

    def points(self, key: TerrainKey, generated: frozenset[Point]) -> frozenset[Point]:
        if key in self.pending:
            return self.pending[key]
        return self.curated.get(key, generated)

    def toggle(
        self, key: TerrainKey, generated: frozenset[Point], point: Point, hit: Callable[[Point], bool]
    ) -> Toggle:
        """Retire l'emplacement touché (`hit`) s'il y en a un, sinon ajoute `point`."""
        current = self.points(key, generated)
        touched = next((existing for existing in sorted(current) if hit(existing)), None)
        if touched is not None:
            self._set(key, generated, current - {touched})
            return Toggle.REMOVED
        self._set(key, generated, current | {point})
        return Toggle.ADDED

    def clear(self, key: TerrainKey, generated: frozenset[Point]) -> None:
        self._set(key, generated, frozenset())

    def merged(self) -> dict[TerrainKey, frozenset[Point]]:
        """Contenu complet de map_spots.csv une fois les modifications appliquées."""
        return {**self.curated, **self.pending}

    def mark_written(self) -> None:
        self.curated = self.merged()
        self.pending = {}

    def shortfalls(self, required: Callable[[TerrainKey], tuple[str, int]]) -> list[Shortfall]:
        """Terrains modifiés qui n'ont pas assez d'emplacements ; `required` donne le nom du lieu et le besoin."""
        result = []
        for key, points in sorted(self.pending.items()):
            name, needed = required(key)
            if len(points) < needed:
                result.append(Shortfall(key, name, len(points), needed))
        return result

    def _set(self, key: TerrainKey, generated: frozenset[Point], points: frozenset[Point]) -> None:
        # Revenir à l'état enregistré annule la modification : le terrain n'est pas figé sans raison.
        if points == self.curated.get(key, generated):
            self.pending.pop(key, None)
        else:
            self.pending[key] = points

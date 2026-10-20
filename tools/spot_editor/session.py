"""État d'édition : emplacements retouchés, modifications en attente et contrôles avant enregistrement."""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum

from pokemaps_data.map_spots import Point, TerrainKey, selected_key


class Toggle(Enum):
    """Effet d'un clic sur la carte."""

    ADDED = "added"
    REMOVED = "removed"


class SpotSession:
    """Emplacements affichés : modification en attente, sinon retouche enregistrée, sinon terrain généré.

    Seuls les terrains réellement modifiés sont mis en attente : un terrain qu'on n'a pas touché reste
    généré (il n'est pas recopié dans map_spots.csv)."""

    def __init__(
        self, curated: dict[TerrainKey, frozenset[Point]], offsets: dict[tuple[str, str], Point] | None = None
    ) -> None:
        self._offsets = dict(offsets or {})
        self.curated = self._translate(curated, 1)
        self.pending: dict[TerrainKey, frozenset[Point]] = {}

    @property
    def has_changes(self) -> bool:
        return bool(self.pending)

    def points(self, key: TerrainKey, generated: frozenset[Point]) -> frozenset[Point]:
        if key in self.pending:
            return self.pending[key]
        return self.curated.get(key, generated)

    def effective_points(self, key: TerrainKey, generated: frozenset[Point]) -> frozenset[Point]:
        return self.points(selected_key(self.merged(), key, key.version_group), generated)

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

    def remove(self, key: TerrainKey, generated: frozenset[Point], point: Point) -> None:
        self._set(key, generated, self.points(key, generated) - {point})

    def merged(self) -> dict[TerrainKey, frozenset[Point]]:
        """Emplacements affichés une fois les modifications appliquées."""
        return {**self.curated, **self.pending}

    def native_points(self) -> dict[TerrainKey, frozenset[Point]]:
        """Le CSV conserve les coordonnées natives, indépendantes de l'assemblage affiché."""
        return self._translate(self.merged(), -1)

    def _translate(
        self, points: dict[TerrainKey, frozenset[Point]], direction: int
    ) -> dict[TerrainKey, frozenset[Point]]:
        return {
            key: frozenset((x + direction * dx, y + direction * dy) for x, y in cells)
            for key, cells in points.items()
            for dx, dy in (self._offsets.get((key.family, key.map_identifier), (0, 0)),)
        }

    def mark_written(self) -> None:
        self.curated = self.merged()
        self.pending = {}

    def _set(self, key: TerrainKey, generated: frozenset[Point], points: frozenset[Point]) -> None:
        # Revenir à l'état enregistré annule la modification : le terrain n'est pas figé sans raison.
        if points == self.curated.get(key, generated):
            self.pending.pop(key, None)
        else:
            self.pending[key] = points

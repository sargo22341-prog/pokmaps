"""Validation locale des emplacements avant écriture, sans génération ni réseau."""

import json
from dataclasses import dataclass
from pathlib import Path

from pokemaps_data.map_spots import Point, TerrainKey, selected_key, write_spots

from .catalog import Family
from .session import SpotSession
from .terrain import WildTerrains


@dataclass(frozen=True)
class SpotError:
    key: TerrainKey
    point: Point | None
    message: str
    # Groupe dont le plan montre l'erreur quand `key` est commune à la famille (vide : le groupe affiché).
    version_group: str = ""

    @property
    def label(self) -> str:
        location = f"{self.point[0]}, {self.point[1]}" if self.point else "terrain"
        scope = f" · {self.key.version_group}" if self.key.version_group else ""
        return f"{self.key.map_identifier}{scope} · {self.key.kind} · {location} : {self.message}"


def spot_errors(session: SpotSession, families: list[Family], terrains: WildTerrains) -> list[SpotError]:
    """Recense toutes les erreurs pour pouvoir les corriger sans recommencer une validation par point."""
    by_family = {family.identifier: family for family in families}
    errors = []
    merged = session.merged()
    for key, points in sorted(merged.items()):
        family = by_family.get(key.family)
        if family is None:
            continue
        groups = tuple(
            group
            for group in family.version_groups
            if (not key.version_group or key.version_group == group) and selected_key(merged, key, group) == key
        )
        if not groups:
            continue
        family = Family(family.identifier, family.label, groups)
        if key.kind not in terrains.kinds(family, key.map_identifier):
            errors.append(SpotError(key, None, "Aucun Pokémon sauvage sur ce terrain"))
            continue
        for point in sorted(points - terrains.points(family, key.map_identifier, key.kind)):
            versions = ", ".join(terrains.rejected_versions(family, key.map_identifier, key.kind, point))
            errors.append(SpotError(key, point, f"Case non retenue pour les rencontres sauvages dans {versions}"))
    return errors


def write_errors(errors: list[SpotError], path: Path) -> None:
    """Rapport local remplaçable, conservé entre les ouvertures de l'éditeur."""
    rows = [
        {
            "family": item.key.family,
            "map": item.key.map_identifier,
            "kind": item.key.kind,
            "version_group": item.key.version_group,
            "point": item.point,
            "message": item.message,
        }
        for item in errors
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def save_spots(session: SpotSession, families: list[Family], terrains: WildTerrains, path: Path) -> None:
    """Refuse les points invalides avant de remplacer le CSV ; conserve les changements en cas d'échec."""
    errors = spot_errors(session, families, terrains)
    if errors:
        raise ValueError(f"{len(errors)} erreur(s). {errors[0].label}. Consultez la liste des erreurs.")
    write_spots(session.merged(), path)
    session.mark_written()

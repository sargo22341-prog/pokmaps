"""Tilesets et collisions de la 2e génération : tuiles, métatuiles, palette de chaque tuile et règles des
collisions (permissions, herbes, glace) lues dans pokegold."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .pret_source import macro_args, parse_int, source_lines

if TYPE_CHECKING:
    from .pret_gen2 import Gen2PretRepo


@dataclass(frozen=True)
class Gen2Tileset:
    const: str
    gfx: Path  # 96 tuiles de 8 px, 16 par ligne, niveaux de gris sur 2 bits
    metatiles: bytes  # 16 octets par métatuile : numéros des 4 × 4 tuiles
    # Collision de chaque quart de métatuile (haut gauche, haut droite, bas gauche, bas droite).
    collisions: tuple[tuple[int, int, int, int], ...]
    palettes: tuple[str | None, ...]  # palette par numéro VRAM ; None pour les emplacements de la police

    def metatile_count(self) -> int:
        return len(self.metatiles) // 16


@dataclass(frozen=True)
class CollisionRules:
    """Ce que le moteur fait de chaque valeur de collision (COLL_…)."""

    values: dict[str, int]  # constante -> valeur
    # Permission de chaque valeur : LAND_TILE, WATER_TILE ou WALL_TILE, suivie de « |TALK » si le joueur interagit
    # avec la case au lieu d'y marcher (data/collision/collision_permissions.asm).
    permissions: tuple[str, ...]
    grass: frozenset[int]  # où l'on rencontre des Pokémon hors des grottes : herbes et eau (CheckGrassCollision)
    ice: frozenset[int]  # glace, où l'on ne rencontre aucun Pokémon (CheckIceTile)
    headbutt_trees: frozenset[int]  # arbres où Coup d'Boule peut faire tomber un Pokémon (CheckHeadbuttTreeTile)


def read_collision_rules(root: Path) -> CollisionRules:
    pattern = re.compile(r"^DEF (COLL_\w+) +EQU +(\$[0-9a-fA-F]+)$")
    values = {
        match.group(1): parse_int(match.group(2))
        for line in source_lines(root / "constants/collision_constants.asm")
        if (match := pattern.match(line))
    }
    permissions = tuple(
        line.removeprefix("db ").replace(" ", "")
        for line in source_lines(root / "data/collision/collision_permissions.asm")
        if line.startswith("db ")
    )
    grass = _routine_args(root / "engine/overworld/tile_events.asm", "CheckGrassCollision::", "db")
    ice = _routine_args(root / "home/map_objects.asm", "CheckIceTile::", "cp")
    trees = _routine_args(root / "home/map_objects.asm", "CheckHeadbuttTreeTile::", "cp")
    return CollisionRules(
        values,
        permissions,
        frozenset(values[name] for name in grass if name != "-1"),
        frozenset(values[name] for name in ice),
        frozenset(values[name] for name in trees),
    )


def read_tilesets(repo: Gen2PretRepo) -> dict[str, Gen2Tileset]:
    """Tilesets du jeu, par constante (TILESET_JOHTO…), d'après data/tilesets.asm."""
    consts = repo.consts("constants/tileset_constants.asm", until="NUM_TILESETS")
    labels = [
        macro_args(line, "tileset")[0]
        for line in source_lines(repo.path("data/tilesets.asm"))
        if line.startswith("tileset ")
    ]
    # La première entrée de la table (Tileset0) précède TILESET_JOHTO = 1.
    if len(labels) != len(consts) + 1:
        raise ValueError(f"{repo.root.name} : {len(labels)} tilesets pour {len(consts)} constantes")
    files = _labelled_files(repo.path("gfx/tilesets.asm")) | _labelled_files(repo.path("gfx/tileset_palette_maps.asm"))
    return {const: _tileset(repo, const, label, files) for const, label in zip(consts, labels[1:], strict=True)}


def _tileset(repo: Gen2PretRepo, const: str, label: str, files: dict[str, str]) -> Gen2Tileset:
    gfx = repo.path(files[f"{label}GFX"].replace(".2bpp.lz", ".png"))
    metatiles = repo.path(files[f"{label}Meta"]).read_bytes()
    values = repo.collisions.values
    collisions = tuple(
        _quarters([values[f"COLL_{name}"] for name in macro_args(line, "tilecoll")])
        for line in source_lines(repo.path(files[f"{label}Coll"]))
        if line.startswith("tilecoll ")
    )
    # Une table de collisions peut décrire plus de métatuiles que le tileset n'en a (entrées jamais lues).
    if len(metatiles) % 16 or len(collisions) < len(metatiles) // 16:
        count = len(metatiles) // 16
        raise ValueError(f"{repo.root.name} : {const} a {count} métatuiles et {len(collisions)} collisions")
    palettes = _tile_palettes(repo.path(files[f"{label}PalMap"]))
    return Gen2Tileset(const, gfx, metatiles, collisions, palettes)


def _tile_palettes(path: Path) -> tuple[str | None, ...]:
    """Cristal charge 96 tuiles par banque ; les numéros $60 à $7f restent réservés à la police."""
    banks: dict[int, list[str]] = {}
    for line in source_lines(path):
        if line.startswith("tilepal "):
            bank, *names = macro_args(line, "tilepal")
            banks.setdefault(parse_int(bank), []).extend(names)
    if set(banks) not in ({0}, {0, 1}) or any(len(names) != 96 for names in banks.values()):
        raise ValueError(f"{path.name} : banques de palettes invalides")
    return (*banks[0], *((None,) * 32 + tuple(banks[1]) if 1 in banks else ()))


def _quarters(values: list[int]) -> tuple[int, int, int, int]:
    top_left, top_right, bottom_left, bottom_right = values
    return top_left, top_right, bottom_left, bottom_right


def _labelled_files(path: Path) -> dict[str, str]:
    """Label -> fichier INCBIN / INCLUDE qui le suit (plusieurs labels peuvent partager le même fichier)."""
    files: dict[str, str] = {}
    pending: list[str] = []
    include = re.compile(r'^(?:INCBIN|INCLUDE) "([^"]+)"$')
    for line in source_lines(path):
        if line.endswith(":"):
            pending.append(line.rstrip(":"))
        elif match := include.match(line):
            files |= {name: match.group(1) for name in pending}
            pending = []
    return files


def _routine_args(path: Path, label: str, opcode: str) -> list[str]:
    """Arguments des instructions `opcode` d'une routine du moteur, de son label au label global suivant (ses
    tables locales, comme .blocks, comprises)."""
    lines = source_lines(path)
    if label not in lines:
        raise ValueError(f"{path.name} : routine {label} introuvable")
    result = []
    for line in lines[lines.index(label) + 1 :]:
        if line.endswith(":") and not line.startswith("."):
            break
        if line.startswith(f"{opcode} "):
            result.append(line.split(maxsplit=1)[1])
    if not result:
        raise ValueError(f"{path.name} : aucune instruction {opcode} dans {label}")
    return result

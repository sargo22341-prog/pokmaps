"""Lecture des désassemblages pret (pokered, pokeyellow) : cartes, tilesets, objets et palettes.

Seuls les fichiers sources texte (.asm), les blocs (.blk, .bst) et les images (.png) du dépôt sont lus :
aucune ROM n'est nécessaire.

Unités : une carte fait `width` × `height` blocs ; un bloc fait 4 × 4 tuiles de 8 px (32 px) ;
les coordonnées des événements (warps, PNJ, objets) sont en pas de 16 px (2 pas par bloc).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

BLOCK_PX = 32
STEP_PX = 16
TILE_PX = 8

# Les cartes extérieures (villes et routes) précèdent la première carte intérieure.
FIRST_INDOOR_MAP = "REDS_HOUSE_1F"
LAST_MAP = "LAST_MAP"

_COMMENT = re.compile(r";.*$")


def _lines(path: Path) -> list[str]:
    """Lignes du fichier sans commentaires ni espaces superflus."""
    return [line for line in (_COMMENT.sub("", raw).strip() for raw in path.read_text("utf-8").splitlines()) if line]


def _args(line: str, macro: str) -> list[str]:
    return [arg.strip() for arg in line[len(macro) :].split(",")]


def _int(value: str) -> int:
    value = value.strip()
    if value.startswith("$"):
        return int(value[1:], 16)
    return int(value)


@dataclass(frozen=True)
class Connection:
    direction: str  # north, south, west, east
    target: str  # constante de la carte voisine (ex. ROUTE_1)
    offset: int  # décalage de la carte voisine, en blocs (x pour nord/sud, y pour ouest/est)


@dataclass(frozen=True)
class Warp:
    x: int
    y: int
    target: str  # constante de la carte d'arrivée, ou LAST_MAP (la carte d'où l'on vient)
    target_warp: int  # numéro du warp d'arrivée, à partir de 1


@dataclass(frozen=True)
class MapObject:
    x: int
    y: int
    kind: str  # npc, item, hidden_item, trainer, pokemon
    sprite: str | None = None  # ex. SPRITE_YOUNGSTER
    item: str | None = None  # ex. MOON_STONE, TM_MEGA_PUNCH
    pokemon: str | None = None  # ex. ZAPDOS
    level: int | None = None
    trainer_class: str | None = None  # ex. OPP_YOUNGSTER


@dataclass
class PretMap:
    const: str
    number: int
    label: str
    width: int
    height: int
    tileset: str
    blocks: bytes
    border_block: int
    is_outdoor: bool
    connections: list[Connection] = field(default_factory=list)
    warps: list[Warp] = field(default_factory=list)
    signs: list[tuple[int, int]] = field(default_factory=list)
    objects: list[MapObject] = field(default_factory=list)

    def block(self, x: int, y: int) -> int:
        return self.blocks[y * self.width + x]


@dataclass(frozen=True)
class Tileset:
    const: str
    gfx: Path  # image des tuiles (16 tuiles de 8 px par ligne, niveaux de gris sur 2 bits)
    blockset: Path  # 16 octets par bloc : numéros des 4 × 4 tuiles


class PretRepo:
    """Données d'un dépôt pret (pokered ou pokeyellow) extrait dans `root`."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def path(self, relative: str) -> Path:
        return self.root / relative

    # --- Constantes -----------------------------------------------------------

    @cached_property
    def map_constants(self) -> dict[str, tuple[int, int, int]]:
        """Constante -> (numéro, largeur, hauteur en blocs)."""
        result = {}
        pattern = re.compile(r"^\s*map_const\s+(\w+),\s*(\d+),\s*(\d+)\s*;\s*\$([0-9A-Fa-f]+)")
        for raw in self.path("constants/map_constants.asm").read_text("utf-8").splitlines():
            match = pattern.match(raw)
            if match:
                name, width, height, number = match.groups()
                result[name] = (int(number, 16), int(width), int(height))
        return result

    @cached_property
    def tileset_order(self) -> list[str]:
        """Constantes des tilesets dans l'ordre (index = numéro du tileset)."""
        consts = []
        started = False
        for line in _lines(self.path("constants/tileset_constants.asm")):
            if line == "const_def":
                started = True
            elif started and line.startswith("const "):
                consts.append(line.split()[1])
            elif started and line.startswith("DEF NUM_TILESETS"):
                break
        return consts

    @cached_property
    def tilesets(self) -> dict[str, Tileset]:
        labels = [
            _args(line, "tileset")[0]
            for line in _lines(self.path("data/tilesets/tileset_headers.asm"))
            if line.startswith("tileset ")
        ]
        if len(labels) != len(self.tileset_order):
            raise ValueError(f"{self.root.name} : {len(labels)} tilesets pour {len(self.tileset_order)} constantes")
        files: dict[str, str] = {}
        pending: list[str] = []
        label_re = re.compile(r"^(\w+_(?:GFX|Block))::")
        incbin_re = re.compile(r'INCBIN\s+"([^"]+)"')
        for line in _lines(self.path("gfx/tilesets.asm")):
            label = label_re.match(line)
            if label:
                pending.append(label.group(1))
            incbin = incbin_re.search(line)
            if incbin:
                for name in pending:
                    files[name] = incbin.group(1)
                pending = []
        result = {}
        for const, label in zip(self.tileset_order, labels, strict=True):
            gfx = files[f"{label}_GFX"].replace(".2bpp", ".png")
            result[const] = Tileset(const, self.path(gfx), self.path(files[f"{label}_Block"]))
        return result

    @cached_property
    def machines(self) -> dict[str, str]:
        """Constante d'objet CT/CS (ex. TM_MEGA_PUNCH) -> identifiant PokéAPI (tm01)."""
        result = {}
        tm = hm = 0
        for line in _lines(self.path("constants/item_constants.asm")):
            if line.startswith("add_tm "):
                tm += 1
                result[f"TM_{line.split()[1]}"] = f"tm{tm:02d}"
            elif line.startswith("add_hm "):
                hm += 1
                result[f"HM_{line.split()[1]}"] = f"hm{hm:02d}"
        return result

    @cached_property
    def palettes(self) -> dict[str, tuple[tuple[int, int, int], ...]]:
        """Palettes Super Game Boy : nom (PAL_ROUTE…) -> 4 couleurs RGB 8 bits, de la plus claire à la plus foncée."""
        result: dict[str, tuple[tuple[int, int, int], ...]] = {}
        pattern = re.compile(r"^\s*RGB\s+([\d,\s]+);\s*(PAL_\w+)")
        for raw in self.path("data/sgb/sgb_palettes.asm").read_text("utf-8").splitlines():
            match = pattern.match(raw)
            if match and match.group(2) not in result:
                values = [int(v) for v in match.group(1).replace(",", " ").split()]
                result[match.group(2)] = tuple(
                    tuple((c << 3) | (c >> 2) for c in values[i : i + 3]) for i in range(0, 12, 3)
                )
        return result

    @cached_property
    def palette_order(self) -> list[str]:
        """Constantes PAL_* dans l'ordre (index = numéro de la palette)."""
        return [
            line.split()[1]
            for line in _lines(self.path("constants/palette_constants.asm"))
            if line.startswith("const PAL_")
        ]

    @cached_property
    def sprites(self) -> dict[str, Path]:
        """Sprite des PNJ (SPRITE_YOUNGSTER…) -> image (frames de 16 × 16 px, la première regarde vers le bas)."""
        files = {}
        pattern = re.compile(r'^(\w+)::\s*INCBIN\s+"([^"]+)\.2bpp"')
        for line in _lines(self.path("gfx/sprites.asm")):
            match = pattern.match(line)
            if match:
                files[match.group(1)] = match.group(2) + ".png"
        result = {}
        pattern = re.compile(r"^\s*overworld_sprite\s+(\w+),\s*\d+\s*;\s*(SPRITE_\w+)")
        for raw in self.path("data/sprites/sprites.asm").read_text("utf-8").splitlines():
            match = pattern.match(raw)
            if match and match.group(1) in files:
                result[match.group(2)] = self.path(files[match.group(1)])
        return result

    # --- Cartes ---------------------------------------------------------------

    @cached_property
    def maps(self) -> dict[str, PretMap]:
        """Toutes les cartes qui ont un en-tête, indexées par constante."""
        blocks = self._block_files()
        objects = self._objects()
        hidden = self._hidden_items()
        result = {}
        for header in sorted(self.path("data/maps/headers").glob("*.asm")):
            lines = _lines(header)
            label, const, tileset = _args(lines[0], "map_header")[:3]
            number, width, height = self.map_constants[const]
            border, warps, signs, objs = objects[label]
            data = self.path(blocks[label]).read_bytes()
            if len(data) > width * height:
                raise ValueError(f"{header.name} : {len(data)} blocs pour {width} × {height}")
            # Quelques fichiers sont plus courts que la carte (le jeu lit alors les octets suivants de la ROM,
            # hors de la zone accessible) : on complète avec le bloc de bordure.
            data += bytes([border]) * (width * height - len(data))
            outdoor = number < self.map_constants[FIRST_INDOOR_MAP][0]
            pret_map = PretMap(
                const, number, label, width, height, tileset, data, border, outdoor, [], warps, signs, objs
            )
            for line in lines[1:]:
                if line.startswith("connection "):
                    direction, _, target, offset = _args(line, "connection")
                    pret_map.connections.append(Connection(direction, target, _int(offset)))
            pret_map.objects += [MapObject(x, y, "hidden_item", item=item) for x, y, item in hidden.get(const, [])]
            result[const] = pret_map
        return result

    def _block_files(self) -> dict[str, str]:
        """Label de carte -> fichier .blk (plusieurs cartes peuvent partager le même fichier)."""
        files = {}
        pending: list[str] = []
        label_re = re.compile(r"^(\w+)_Blocks:")
        incbin_re = re.compile(r'INCBIN\s+"([^"]+\.blk)"')
        for line in _lines(self.path("maps.asm")):
            label = label_re.match(line)
            if label:
                pending.append(label.group(1))
            incbin = incbin_re.search(line)
            if incbin:
                for name in pending:
                    files[name] = incbin.group(1)
                pending = []
        return files

    def _objects(self) -> dict[str, tuple[int, list[Warp], list[tuple[int, int]], list[MapObject]]]:
        result = {}
        for path in sorted(self.path("data/maps/objects").glob("*.asm")):
            label = None
            border = 0
            warps: list[Warp] = []
            signs: list[tuple[int, int]] = []
            objs: list[MapObject] = []
            for line in _lines(path):
                if line.endswith("_Object:"):
                    label = line[: -len("_Object:")]
                elif line.startswith("db $") and label and not warps and not objs:
                    border = _int(line[3:])
                elif line.startswith("warp_event "):
                    x, y, target, target_warp = _args(line, "warp_event")
                    warps.append(Warp(int(x), int(y), target, int(target_warp)))
                elif line.startswith("bg_event "):
                    x, y, _ = _args(line, "bg_event")
                    signs.append((int(x), int(y)))
                elif line.startswith("object_event "):
                    objs.append(_object_event(_args(line, "object_event")))
                elif line.startswith("def_warps_to"):
                    break
            if label is None:
                raise ValueError(f"{path.name} : label _Object introuvable")
            result[label] = (border, warps, signs, objs)
        return result

    def _hidden_items(self) -> dict[str, list[tuple[int, int, str]]]:
        """Objets cachés (Cherch'Objet) : constante de carte -> [(x, y, objet)]."""
        result: dict[str, list[tuple[int, int, str]]] = {}
        current = None
        for line in _lines(self.path("data/events/hidden_events.asm")):
            if line.startswith("hidden_events_for "):
                current = line.split()[1]
            elif line.startswith("hidden_event ") and current:
                x, y, function, argument = _args(line, "hidden_event")
                if function == "HiddenItems":
                    result.setdefault(current, []).append((int(x), int(y), argument))
        return result


def _object_event(args: list[str]) -> MapObject:
    x, y, sprite = int(args[0]), int(args[1]), args[2]
    if len(args) == 8:
        if args[6].startswith("OPP_"):
            return MapObject(x, y, "trainer", sprite, trainer_class=args[6])
        return MapObject(x, y, "pokemon", sprite, pokemon=args[6], level=int(args[7]))
    if len(args) == 7 and args[6] != "0":
        return MapObject(x, y, "item", sprite, item=args[6])
    return MapObject(x, y, "npc", sprite)

"""Lecture des désassemblages pret (pokered, pokeyellow) : cartes, tilesets, objets et palettes.

Seuls les fichiers sources texte (.asm), les blocs (.blk, .bst) et les images (.png) du dépôt sont lus :
aucune ROM n'est nécessaire.

Unités : une carte fait `width` × `height` blocs ; un bloc fait 4 × 4 tuiles de 8 px (32 px) ;
les coordonnées des événements (warps, PNJ, objets) sont en pas de 16 px (2 pas par bloc).
"""

from __future__ import annotations

import re
from functools import cached_property
from pathlib import Path

from .games import KANTO
from .pret_conditions import Gen1Conditions
from .pret_models import (
    Connection,
    LocatedLine,
    MapObject,
    NpcOffer,
    PretMap,
    ScriptIndex,
    Tileset,
    TrainerPokemon,
    Warp,
    merged_offers,
)
from .pret_source import macro_args, parse_int, source_lines
from .pret_trainers import (
    GYM_LEADER_PARTIES,
    GYM_LEADERS,
    base_moves,
    default_moves,
    learnsets,
    trainer_parties,
)

BLOCK_PX = 32
STEP_PX = 16
TILE_PX = 8

# Tuile d'eau ou l'on peut surfer (CollisionCheckOnWater dans home/overworld.asm).
WATER_TILE = 0x14

# Les cartes extérieures (villes et routes) précèdent la première carte intérieure.
FIRST_INDOOR_MAP = "REDS_HOUSE_1F"
LAST_MAP = "LAST_MAP"


# Instructions d'appel suivies pour lire tout ce que fait un texte, et profondeur maximale suivie.
CALLS = frozenset({"farcall", "callfar", "call", "jp"})
TEXT_CALL_DEPTH = 2


__all__ = [
    "BLOCK_PX",
    "FIRST_INDOOR_MAP",
    "GYM_LEADERS",
    "GYM_LEADER_PARTIES",
    "LAST_MAP",
    "STEP_PX",
    "TILE_PX",
    "WATER_TILE",
    "Connection",
    "MapObject",
    "NpcOffer",
    "PretMap",
    "PretRepo",
    "Tileset",
    "TrainerPokemon",
    "Warp",
]


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
        for line in source_lines(self.path("constants/tileset_constants.asm")):
            if line == "const_def":
                started = True
            elif started and line.startswith("const "):
                consts.append(line.split()[1])
            elif started and line.startswith("DEF NUM_TILESETS"):
                break
        return consts

    @cached_property
    def tilesets(self) -> dict[str, Tileset]:
        headers = [
            macro_args(line, "tileset")
            for line in source_lines(self.path("data/tilesets/tileset_headers.asm"))
            if line.startswith("tileset ")
        ]
        labels = [header[0] for header in headers]
        if len(labels) != len(self.tileset_order):
            raise ValueError(f"{self.root.name} : {len(labels)} tilesets pour {len(self.tileset_order)} constantes")
        files: dict[str, str] = {}
        pending: list[str] = []
        label_re = re.compile(r"^(\w+_(?:GFX|Block))::")
        incbin_re = re.compile(r'INCBIN\s+"([^"]+)"')
        for line in source_lines(self.path("gfx/tilesets.asm")):
            label = label_re.match(line)
            if label:
                pending.append(label.group(1))
            incbin = incbin_re.search(line)
            if incbin:
                for name in pending:
                    files[name] = incbin.group(1)
                pending = []
        collisions = self._collision_tiles()
        water = self._water_tilesets()
        result = {}
        for const, header in zip(self.tileset_order, headers, strict=True):
            label = header[0]
            gfx = files[f"{label}_GFX"].replace(".2bpp", ".png")
            grass = parse_int(header[4]) if header[4] != "-1" else None
            result[const] = Tileset(
                const,
                self.path(gfx),
                self.path(files[f"{label}_Block"]),
                grass,
                collisions.get(f"{label}_Coll", frozenset()),
                const in water,
            )
        return result

    def _collision_tiles(self) -> dict[str, frozenset[int]]:
        """Label `<Tileset>_Coll` -> tuiles où l'on peut marcher (plusieurs labels peuvent partager une liste)."""
        result: dict[str, frozenset[int]] = {}
        pending: list[str] = []
        for line in source_lines(self.path("data/tilesets/collision_tile_ids.asm")):
            if line.endswith("::"):
                pending.append(line[:-2])
            elif line.startswith("coll_tiles") and pending:
                tiles = frozenset(parse_int(arg) for arg in macro_args(line, "coll_tiles") if arg)
                for label in pending:
                    result[label] = tiles
                pending = []
        return result

    @cached_property
    def land_pair_collisions(self) -> dict[str, set[frozenset[int]]]:
        """Tileset -> paires de tuiles entre lesquelles on ne peut pas marcher (différence de hauteur)."""
        result: dict[str, set[frozenset[int]]] = {}
        section = None
        for line in source_lines(self.path("data/tilesets/pair_collision_tile_ids.asm")):
            if line.endswith("::"):
                section = line[:-2]
            elif section == "TilePairCollisionsLand" and line.startswith("db ") and line != "db -1":
                tileset, first, second = macro_args(line, "db")
                result.setdefault(tileset, set()).add(frozenset((parse_int(first), parse_int(second))))
        return result

    def _water_tilesets(self) -> set[str]:
        return {
            line.split()[1]
            for line in source_lines(self.path("data/tilesets/water_tilesets.asm"))
            if line.startswith("db ") and line.split()[1] != "-1"
        }

    def tile_at(self, pret_map: PretMap, tx: int, ty: int) -> int:
        """Numéro de la tuile (8 px) en (tx, ty) d'une carte."""
        data = self._blockset(pret_map.tileset)
        block = pret_map.block(tx // 4, ty // 4)
        return data[block * 16 + (ty % 4) * 4 + tx % 4]

    def _blockset(self, tileset: str) -> bytes:
        cache = self.__dict__.setdefault("_blockset_cache", {})
        if tileset not in cache:
            cache[tileset] = self.tilesets[tileset].blockset.read_bytes()
        return cache[tileset]

    @cached_property
    def machines(self) -> dict[str, str]:
        """Constante d'objet CT/CS (ex. TM_MEGA_PUNCH) -> identifiant PokéAPI (tm01)."""
        result = {}
        tm = hm = 0
        for line in source_lines(self.path("constants/item_constants.asm")):
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
            for line in source_lines(self.path("constants/palette_constants.asm"))
            if line.startswith("const PAL_")
        ]

    @cached_property
    def sprites(self) -> dict[str, Path]:
        """Sprite des PNJ (SPRITE_YOUNGSTER…) -> image (frames de 16 × 16 px, la première regarde vers le bas)."""
        files = {}
        pattern = re.compile(r'^(\w+)::\s*INCBIN\s+"([^"]+)\.2bpp"')
        for line in source_lines(self.path("gfx/sprites.asm")):
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

    # --- Dresseurs --------------------------------------------------------------

    def consts(self, relative: str, macro: str = "const") -> list[str]:
        """Constantes d'un fichier `const_def` dans l'ordre (index = valeur)."""
        return [line.split()[1] for line in source_lines(self.path(relative)) if line.startswith(f"{macro} ")]

    @cached_property
    def base_moves(self) -> dict[str, tuple[str, ...]]:
        return base_moves(self)

    @cached_property
    def learnsets(self) -> dict[str, list[tuple[int, str]]]:
        return learnsets(self)

    def default_moves(self, species: str, level: int) -> list[str]:
        return default_moves(self, species, level)

    @cached_property
    def trainer_parties(self) -> dict[tuple[str, int], list[TrainerPokemon]]:
        return trainer_parties(self)

    # --- Personnages : dons, boutiques, échanges --------------------------------

    @cached_property
    def script_index(self) -> ScriptIndex:
        """Labels de texte ou de script, leurs lignes jusqu'au label suivant et ce label suivant, où l'exécution
        continue faute de saut (scripts/ et data/items/marts.asm)."""
        files = [*sorted(self.path("scripts").glob("*.asm")), self.path("data/items/marts.asm")]
        bodies: dict[str, list[str]] = {}
        following: dict[str, str] = {}
        label_re = re.compile(r"^([A-Za-z_]\w*)::?$")
        for path in files:
            current = None
            for line in source_lines(path):
                match = label_re.match(line)
                if match:
                    if current:
                        following[current] = match.group(1)
                    current = match.group(1)
                    bodies[current] = []
                elif current:
                    bodies[current].append(line)
        return ScriptIndex(bodies, following)

    @property
    def _script_bodies(self) -> dict[str, list[str]]:
        return self.script_index.bodies

    @cached_property
    def _text_labels(self) -> dict[str, str]:
        """Constante de texte (TEXT_…) -> label du texte (dw_const des scripts)."""
        result = {}
        for path in sorted(self.path("scripts").glob("*.asm")):
            for line in source_lines(path):
                if line.startswith("dw_const "):
                    label, const = macro_args(line, "dw_const")[:2]
                    result[const] = label
        return result

    @cached_property
    def prices(self) -> dict[str, int]:
        """Objet -> prix en magasin (data/items/prices.asm et tm_prices.asm)."""
        result = {}
        price_re = re.compile(r"^\s*bcd3\s+(\d+)\s*;\s*(\w+)")
        for raw in self.path("data/items/prices.asm").read_text("utf-8").splitlines():
            if match := price_re.match(raw):
                result[match.group(2)] = int(match.group(1))
        tm_re = re.compile(r"^\s*nybble\s+(\d+)\s*;\s*TM(\d+)")
        tms = {int(number): f"TM_{name}" for name, number in self._tm_numbers.items()}
        for raw in self.path("data/items/tm_prices.asm").read_text("utf-8").splitlines():
            if (match := tm_re.match(raw)) and int(match.group(2)) in tms:
                result[tms[int(match.group(2))]] = int(match.group(1)) * 1000
        return result

    @cached_property
    def _tm_numbers(self) -> dict[str, int]:
        numbers = {}
        for line in source_lines(self.path("constants/item_constants.asm")):
            if line.startswith("add_tm "):
                numbers[line.split()[1]] = len(numbers) + 1
        return numbers

    @cached_property
    def trades(self) -> list[tuple[str, str]]:
        """Échanges en jeu (Pokémon demandé, Pokémon reçu), dans l'ordre des constantes TRADE_FOR_*."""
        return [
            tuple(macro_args(line, "npctrade")[:2])
            for line in source_lines(self.path("data/events/trades.asm"))
            if line.startswith("npctrade ")
        ]

    @cached_property
    def _trade_index(self) -> dict[str, int]:
        consts = [
            line.split()[1]
            for line in source_lines(self.path("constants/script_constants.asm"))
            if line.startswith("const TRADE_FOR_")
        ]
        return {const: index for index, const in enumerate(consts)}

    def _expanded_body(self, label: str | None, depth: int) -> list[LocatedLine]:
        """Lignes d'un texte, en suivant les appels vers d'autres textes ou scripts (farcall Route1PrintText,
        jp nz, RedsHouse1FMomHealScript…). `depth` borne la profondeur des appels suivis."""
        body = self._script_bodies.get(label or "", [])
        result: list[LocatedLine] = []
        for index, line in enumerate(body):
            result.append(LocatedLine(label or "", index, line))
            if depth == 0:
                continue
            parts = line.replace(",", " ").split()
            target = parts[-1] if parts else None
            if parts and parts[0] in CALLS and target in self._script_bodies and target != label:
                result += self._expanded_body(target, depth - 1)
        return result

    def located_text_body(self, text: str | None) -> list[LocatedLine]:
        """Lignes exécutées quand le joueur lit ce texte (constante TEXT_…), appels compris, avec leur place."""
        return self._expanded_body(self._text_labels.get(text or ""), depth=TEXT_CALL_DEPTH)

    def text_body(self, text: str | None) -> list[str]:
        """Lignes exécutées quand le joueur lit ce texte (constante TEXT_…), appels compris."""
        return [located.line for located in self.located_text_body(text)]

    def script_body(self, label: str) -> list[str]:
        """Lignes d'un label des scripts (ex. FossilsList), sans suivre ses appels."""
        if label not in self._script_bodies:
            raise ValueError(f"{self.root.name} : label {label} introuvable dans scripts/")
        return self._script_bodies[label]

    def text_label(self, text: str | None) -> str | None:
        """Label du texte affiché pour la constante TEXT_…, None s'il n'est dans aucun script."""
        return self._text_labels.get(text or "")

    def leader_gifts(self, map_label: str) -> list[NpcOffer]:
        """CT donnée par le champion d'une arène après le combat (script de la carte, pas de son texte)."""
        path = self.path(f"scripts/{map_label}.asm")
        if not path.exists():
            return []
        offers = []
        pending = None
        for line in source_lines(path):
            if line.startswith("lb bc,"):
                args = macro_args(line, "lb bc,")
                pending = (args[0], parse_int(args[1])) if len(args) == 2 and args[0].startswith("TM_") else None
            elif line == "call GiveItem" and pending:
                offers.append(NpcOffer("gift_item", item=pending[0], quantity=pending[1]))
        return list(dict.fromkeys(offers))

    @cached_property
    def conditions(self) -> Gen1Conditions:
        return Gen1Conditions(self)

    def npc_offers(self, text: str | None) -> list[NpcOffer]:
        """Objets donnés ou vendus, Pokémon donnés ou échangés par le personnage qui affiche ce texte, chacun avec
        ce qu'exige le texte pour le proposer."""
        place = self.conditions.offer_place(text)
        offers: list[NpcOffer] = []
        pending: tuple[str, int] | None = None
        for located in self.located_text_body(text):
            line = located.line
            if line.startswith("script_mart "):
                offers += [
                    place.at(located, NpcOffer("sale", item=item, price=self.prices.get(item)))
                    for item in macro_args(line, "script_mart")
                ]
            elif line.startswith("lb bc,"):
                args = macro_args(line, "lb bc,")
                pending = (args[0], parse_int(args[1])) if len(args) == 2 and not args[1].startswith("[") else None
            elif line == "call GiveItem" and pending:
                offers.append(place.at(located, NpcOffer("gift_item", item=pending[0], quantity=pending[1])))
            elif line == "call GivePokemon" and pending:
                offers.append(place.at(located, NpcOffer("gift_pokemon", pokemon=pending[0], quantity=pending[1])))
            elif line.startswith("ld a, TRADE_FOR_"):
                index = self._trade_index.get(line.split(",")[1].strip())
                if index is not None and index < len(self.trades):
                    wanted, given = self.trades[index]
                    offers.append(place.at(located, NpcOffer("trade", pokemon=given, wanted=wanted)))
        return merged_offers(offers)

    # --- Cartes ---------------------------------------------------------------

    def map_region(self, const: str) -> str:
        """Région de la carte : toutes celles de Rouge, Bleu et Jaune sont en Kanto."""
        if const not in self.maps:
            raise ValueError(f"{self.root.name} : carte inconnue {const}")
        return KANTO.const

    @cached_property
    def maps(self) -> dict[str, PretMap]:
        from .pret_maps import maps

        return maps(self)

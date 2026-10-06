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

from .pret_models import Connection, MapObject, NpcOffer, PretMap, Tileset, TrainerPokemon, Warp
from .pret_source import macro_args, parse_int, source_lines

BLOCK_PX = 32
STEP_PX = 16
TILE_PX = 8

# Tuile d'eau ou l'on peut surfer (CollisionCheckOnWater dans home/overworld.asm).
WATER_TILE = 0x14

# Les cartes extérieures (villes et routes) précèdent la première carte intérieure.
FIRST_INDOOR_MAP = "REDS_HOUSE_1F"
LAST_MAP = "LAST_MAP"


# Champions d'arène dans l'ordre de wGymLeaderNo (LoneMoves de Rouge / Bleu), avec leur équipe d'arène.
GYM_LEADERS = ("BROCK", "MISTY", "LT_SURGE", "ERIKA", "KOGA", "SABRINA", "BLAINE", "GIOVANNI")
GYM_LEADER_PARTIES = {(leader, 3 if leader == "GIOVANNI" else 1) for leader in GYM_LEADERS}


__all__ = [
    "BLOCK_PX",
    "FIRST_INDOOR_MAP",
    "GYM_LEADERS",
    "GYM_LEADER_PARTIES",
    "LAST_MAP",
    "MapObject",
    "NpcOffer",
    "PretMap",
    "PretRepo",
    "STEP_PX",
    "TILE_PX",
    "Tileset",
    "TrainerPokemon",
    "WATER_TILE",
    "Warp",
    "Connection",
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

    def _consts(self, relative: str, macro: str = "const") -> list[str]:
        """Constantes d'un fichier `const_def` dans l'ordre (index = valeur)."""
        return [line.split()[1] for line in source_lines(self.path(relative)) if line.startswith(f"{macro} ")]

    @cached_property
    def base_moves(self) -> dict[str, tuple[str, ...]]:
        """Pokémon -> attaques connues au niveau 1 (data/pokemon/base_stats)."""
        result = {}
        species_re = re.compile(r"^\s*db\s+DEX_(\w+)")
        moves_re = re.compile(r"^\s*db\s+([\w,\s]+?)\s*;\s*level 1 learnset")
        for path in sorted(self.path("data/pokemon/base_stats").glob("*.asm")):
            species = moves = None
            for raw in path.read_text("utf-8").splitlines():
                if species is None and (match := species_re.match(raw)):
                    species = match.group(1)
                elif match := moves_re.match(raw):
                    moves = tuple(m.strip() for m in match.group(1).split(",") if m.strip() != "NO_MOVE")
            if species and moves is not None:
                result[species] = moves
        return result

    @cached_property
    def learnsets(self) -> dict[str, list[tuple[int, str]]]:
        """Pokémon -> attaques apprises par niveau, dans l'ordre (data/pokemon/evos_moves.asm)."""
        lines = source_lines(self.path("data/pokemon/evos_moves.asm"))
        # Les labels portent le nom du Pokémon (NidoranMEvosMoves -> NIDORAN_M).
        species = {const.replace("_", ""): const for const in self._consts("constants/pokemon_constants.asm")}
        by_label = {
            label: species[label.removesuffix("EvosMoves").upper()]
            for label in (line.split()[1] for line in lines if line.startswith("dw ") and line.endswith("EvosMoves"))
            if label.removesuffix("EvosMoves").upper() in species
        }
        result: dict[str, list[tuple[int, str]]] = {}
        current = None
        zeros = 0
        for line in lines:
            if line.endswith(":") and line[:-1] in by_label:
                current, zeros = by_label[line[:-1]], 0
                result[current] = []
            elif current and line.startswith("db "):
                args = macro_args(line, "db")
                if args == ["0"]:
                    zeros += 1
                    if zeros == 2:
                        current = None
                elif zeros == 1 and len(args) == 2:
                    result[current].append((parse_int(args[0]), args[1]))
        return result

    def default_moves(self, species: str, level: int) -> list[str]:
        """Attaques d'un Pokémon de dresseur à ce niveau (WriteMonMoves : les 4 dernières apprises)."""
        moves = list(self.base_moves.get(species, ()))
        for learn_level, move in self.learnsets.get(species, []):
            if learn_level > level or move in moves:
                continue
            if len(moves) == 4:
                moves.pop(0)
            moves.append(move)
        return moves

    @cached_property
    def trainer_parties(self) -> dict[tuple[str, int], list[TrainerPokemon]]:
        """(classe, numéro) -> équipe, attaques comprises (data/trainers/parties.asm et special_moves.asm)."""
        lines = source_lines(self.path("data/trainers/parties.asm"))
        classes = self._consts("constants/trainer_constants.asm", "trainer_const")[1:]
        labels = [line.split()[1] for line in lines if line.startswith("dw ") and line.endswith("Data")]
        by_label = dict(zip(labels, classes, strict=True))
        raw: dict[tuple[str, int], list[tuple[int, str]]] = {}
        current = None
        number = 0
        for line in lines:
            if line.endswith(":") and line[:-1] in by_label:
                current, number = by_label[line[:-1]], 0
            elif current and line.startswith("db "):
                args = macro_args(line, "db")
                if args[-1] != "0":
                    raise ValueError(f"parties.asm : équipe non terminée par 0 : {line}")
                number += 1
                args = args[:-1]
                if args[0] == "$FF":
                    pairs = [(parse_int(args[i]), args[i + 1]) for i in range(1, len(args), 2)]
                else:
                    pairs = [(parse_int(args[0]), species) for species in args[1:]]
                raw[(current, number)] = pairs
        parties = {
            key: [[species, level, self.default_moves(species, level)] for level, species in pairs]
            for key, pairs in raw.items()
        }
        self._apply_special_moves(parties, raw)
        return {
            key: [TrainerPokemon(species, level, tuple(moves)) for species, level, moves in party]
            for key, party in parties.items()
        }

    def _apply_special_moves(self, parties: dict, raw: dict) -> None:
        def put(key: tuple[str, int], mon: int, slot: int, move: str) -> None:
            party = parties.get(key)
            if party is None or mon >= len(party):
                return
            moves = party[mon][2]
            while len(moves) <= slot:
                moves.append("NO_MOVE")
            moves[slot] = move

        lines = source_lines(self.path("data/trainers/special_moves.asm"))
        if any(line.startswith("SpecialTrainerMoves") for line in lines):
            # Jaune : « db classe, numéro » puis « db Pokémon, emplacement, attaque » (à partir de 1), « db 0 ».
            key = None
            for line in lines:
                if not line.startswith("db "):
                    continue
                args = macro_args(line, "db")
                if len(args) == 2:
                    key = (args[0], parse_int(args[1]))
                elif len(args) == 3 and key:
                    put(key, parse_int(args[0]) - 1, parse_int(args[1]) - 1, args[2])
        else:
            # Rouge / Bleu : attaque unique d'un champion d'arène (LoneMoves, 3e attaque du Pokémon n + 1)
            # et attaque du Conseil 4 (TeamMoves, 3e attaque du 5e Pokémon).
            section = None
            lone = []
            team = {}
            for line in lines:
                if line.endswith(":"):
                    section = line[:-1]
                elif line.startswith("db "):
                    args = macro_args(line, "db")
                    if section == "LoneMoves" and len(args) == 2:
                        lone.append((parse_int(args[0]), args[1]))
                    elif section == "TeamMoves" and len(args) == 2:
                        team[args[0]] = args[1]
            for leader, (mon, move) in zip(GYM_LEADERS, lone, strict=False):
                for key in raw:
                    if key[0] == leader and key in GYM_LEADER_PARTIES:
                        put(key, mon, 2, move)
            for trainer_class, move in team.items():
                for key in raw:
                    if key[0] == trainer_class:
                        put(key, 4, 2, move)
        for party in parties.values():
            for mon in party:
                mon[2] = [move for move in mon[2] if move != "NO_MOVE"]

    # --- Personnages : dons, boutiques, échanges --------------------------------

    @cached_property
    def _script_bodies(self) -> dict[str, list[str]]:
        """Label de texte ou de script -> ses lignes, jusqu'au label suivant (scripts/ et data/items/marts.asm)."""
        files = [*sorted(self.path("scripts").glob("*.asm")), self.path("data/items/marts.asm")]
        bodies: dict[str, list[str]] = {}
        label_re = re.compile(r"^([A-Za-z_]\w*)::?$")
        for path in files:
            current = None
            for line in source_lines(path):
                match = label_re.match(line)
                if match:
                    current = match.group(1)
                    bodies[current] = []
                elif current:
                    bodies[current].append(line)
        return bodies

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

    def _expanded_body(self, label: str | None, depth: int) -> list[str]:
        """Lignes d'un texte, en suivant les appels vers d'autres textes ou scripts (farcall Route1PrintText…)."""
        body = self._script_bodies.get(label or "", [])
        if depth == 0:
            return body
        result = []
        for line in body:
            result.append(line)
            parts = line.replace(",", " ").split()
            target = parts[-1] if parts else None
            if parts and parts[0] in ("farcall", "callfar") and target in self._script_bodies and target != label:
                result += self._expanded_body(target, depth - 1)
        return result

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

    def npc_offers(self, text: str | None) -> list[NpcOffer]:
        """Objets donnés ou vendus, Pokémon donnés ou échangés par le personnage qui affiche ce texte."""
        label = self._text_labels.get(text or "")
        offers: list[NpcOffer] = []
        pending: tuple[str, int] | None = None
        for line in self._expanded_body(label, depth=2):
            if line.startswith("script_mart "):
                offers += [
                    NpcOffer("sale", item=item, price=self.prices.get(item)) for item in macro_args(line, "script_mart")
                ]
            elif line.startswith("lb bc,"):
                args = macro_args(line, "lb bc,")
                pending = (args[0], parse_int(args[1])) if len(args) == 2 and not args[1].startswith("[") else None
            elif line == "call GiveItem" and pending:
                offers.append(NpcOffer("gift_item", item=pending[0], quantity=pending[1]))
            elif line == "call GivePokemon" and pending:
                offers.append(NpcOffer("gift_pokemon", pokemon=pending[0], quantity=pending[1]))
            elif line.startswith("ld a, TRADE_FOR_"):
                index = self._trade_index.get(line.split(",")[1].strip())
                if index is not None and index < len(self.trades):
                    wanted, given = self.trades[index]
                    offers.append(NpcOffer("trade", pokemon=given, wanted=wanted))
        return list(dict.fromkeys(offers))

    # --- Cartes ---------------------------------------------------------------

    @cached_property
    def maps(self) -> dict[str, PretMap]:
        from .pret_maps import maps

        return maps(self)

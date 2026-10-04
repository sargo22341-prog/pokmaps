"""Lecture des données de jeu depuis les désassemblages pret (pokered / pokeyellow).

Chaque `PretGame` correspond à une version : Rouge et Bleu partagent le dépôt pokered
(différenciés par `_RED` / `_BLUE`), Jaune utilise pokeyellow.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

from .asm import (
    directive,
    labelled_blocks,
    parse_constants,
    parse_number,
    read_lines,
    split_args,
)

# Méthodes de rencontre stockées dans la base.
WALK = "WALK"  # herbes hautes, grottes, bâtiments
SURF = "SURF"
OLD_ROD = "OLD_ROD"
GOOD_ROD = "GOOD_ROD"
SUPER_ROD = "SUPER_ROD"
STATIC = "STATIC"
TRADE = "TRADE"
PRIZE = "PRIZE"

# Canne : toujours un Magicarpe niveau 5 (engine/items/item_effects.asm, ItemUseOldRod).
OLD_ROD_ENCOUNTER = ("MAGIKARP", 5)

# Super Canne de Jaune : seuils aléatoires de GenerateRandomFishingEncounter
# (engine/items/super_rod.asm : cp $66, cp $b2, cp $e5) -> probabilités des 4 emplacements.
YELLOW_SUPER_ROD_SLOT_CHANCES = (0x66, 0xB2 - 0x66, 0xE5 - 0xB2, 0x100 - 0xE5)


@dataclass(frozen=True)
class BaseStats:
    species: str
    hp: int
    attack: int
    defense: int
    speed: int
    special: int
    types: tuple[str, ...]
    catch_rate: int
    base_exp: int
    start_moves: tuple[str, ...]
    growth_rate: str
    tmhm: tuple[str, ...]


@dataclass(frozen=True)
class Evolution:
    method: str  # LEVEL, ITEM, TRADE
    species: str
    level: int | None = None
    item: str | None = None


@dataclass(frozen=True)
class EvosMoves:
    evolutions: tuple[Evolution, ...]
    learnset: tuple[tuple[int, str], ...]  # (niveau, attaque)


@dataclass(frozen=True)
class Move:
    name: str
    effect: str
    power: int
    type: str
    accuracy: int
    pp: int


@dataclass(frozen=True)
class Slot:
    """Un emplacement de rencontre : espèce, niveau et probabilité (en 1/256 ou fraction)."""

    species: str
    level: int
    chance: float  # en pourcentage


@dataclass(frozen=True)
class EncounterTable:
    map_name: str
    method: str
    rate: int | None  # taux de rencontre par pas (sur 256), None pour la pêche
    slots: tuple[Slot, ...]


@dataclass(frozen=True)
class Trade:
    map_name: str
    give: str
    get: str
    nickname: str


@dataclass(frozen=True)
class Prize:
    species: str
    level: int
    cost: int


@dataclass(frozen=True)
class StaticEncounter:
    map_name: str
    species: str
    level: int
    count: int = 1


@dataclass
class PretGame:
    root: Path
    defines: set[str] = field(default_factory=set)

    @property
    def is_yellow(self) -> bool:
        return "_YELLOW" in self.defines

    def _lines(self, relative: str) -> list[str]:
        return read_lines(self.root / relative, self.defines)

    # --- Constantes ---------------------------------------------------------

    @cached_property
    def species_ids(self) -> dict[str, int]:
        """Espèce (constante interne) -> index interne du jeu."""
        return parse_constants(self.root / "constants/pokemon_constants.asm")

    @cached_property
    def dex_numbers(self) -> dict[str, int]:
        """Espèce (constante sans le préfixe DEX_) -> numéro du Pokédex national."""
        dex = parse_constants(self.root / "constants/pokedex_constants.asm")
        return {name.removeprefix("DEX_"): number for name, number in dex.items()}

    @cached_property
    def move_ids(self) -> dict[str, int]:
        moves = parse_constants(self.root / "constants/move_constants.asm")
        moves.pop("NO_MOVE", None)
        return moves

    @cached_property
    def map_ids(self) -> dict[str, int]:
        return parse_constants(self.root / "constants/map_constants.asm", ("map_const",))

    @cached_property
    def item_ids(self) -> dict[str, int]:
        return parse_constants(self.root / "constants/item_constants.asm")

    @cached_property
    def machines(self) -> list[tuple[str, int, str]]:
        """Liste des (TM|HM, numéro, attaque) dans l'ordre du jeu."""
        tms: list[tuple[str, int, str]] = []
        hms: list[tuple[str, int, str]] = []
        for line in self._lines("constants/item_constants.asm"):
            name, args = directive(line)
            if name == "add_tm":
                tms.append(("TM", len(tms) + 1, args[0]))
            elif name == "add_hm":
                hms.append(("HM", len(hms) + 1, args[0]))
        return tms + hms

    def dex_of(self, species: str) -> int:
        return self.dex_numbers[species]

    # --- Pokémon ------------------------------------------------------------

    @cached_property
    def base_stats(self) -> dict[str, BaseStats]:
        """Espèce -> statistiques de base."""
        result: dict[str, BaseStats] = {}
        for path in sorted((self.root / "data/pokemon/base_stats").glob("*.asm")):
            stats = _parse_base_stats(read_lines(path, self.defines))
            result[stats.species] = stats
        return result

    @cached_property
    def evos_moves(self) -> dict[str, EvosMoves]:
        """Espèce -> évolutions et attaques apprises par niveau."""
        lines = self._lines("data/pokemon/evos_moves.asm")
        blocks = labelled_blocks(lines)
        pointers = [directive(line)[1][0] for line in blocks["EvosMovesPointerTable"] if line.startswith("dw ")]
        by_index = {index: name for name, index in self.species_ids.items()}
        result: dict[str, EvosMoves] = {}
        for index, label in enumerate(pointers, start=1):
            species = by_index.get(index)
            if species is None or species not in self.dex_numbers:
                continue  # MissingNo.
            result[species] = _parse_evos_moves(blocks[label])
        return result

    @cached_property
    def moves(self) -> dict[str, Move]:
        result: dict[str, Move] = {}
        for line in self._lines("data/moves/moves.asm"):
            name, args = directive(line)
            if name != "move":
                continue
            move = Move(
                name=args[0],
                effect=args[1],
                power=parse_number(args[2]),
                type=args[3],
                accuracy=parse_number(args[4].split()[0]),
                pp=parse_number(args[5]),
            )
            result[move.name] = move
        return result

    # --- Rencontres ---------------------------------------------------------

    @cached_property
    def wild_slot_chances(self) -> list[int]:
        """Probabilités (sur 256) des 10 emplacements herbe/surf."""
        chances = []
        for line in self._lines("data/wild/probabilities.asm"):
            name, args = directive(line)
            if name == "wild_chance":
                chances.append(parse_number(args[0]))
        if sum(chances) != 256:
            raise ValueError(f"Probabilités sauvages incohérentes : {chances}")
        return chances

    @cached_property
    def wild_encounters(self) -> list[EncounterTable]:
        pointer_lines = labelled_blocks(self._lines("data/wild/grass_water.asm"))["WildDataPointers"]
        pointers = [directive(line)[1][0] for line in pointer_lines if line.startswith("dw ")]
        map_by_index = {index: name for name, index in self.map_ids.items()}

        lines: list[str] = []
        for path in sorted((self.root / "data/wild/maps").glob("*.asm")):
            lines += read_lines(path, self.defines)
        blocks = labelled_blocks(lines)

        tables: list[EncounterTable] = []
        for index, label in enumerate(pointers):
            if label == "NothingWildMons" or index not in map_by_index:
                continue
            tables += self._parse_wild_block(map_by_index[index], blocks[label])
        return tables

    def _parse_wild_block(self, map_name: str, lines: list[str]) -> list[EncounterTable]:
        tables = []
        method: str | None = None
        rate = 0
        slots: list[tuple[int, str]] = []
        for line in lines:
            name, args = directive(line)
            if name in ("def_grass_wildmons", "def_water_wildmons"):
                method = WALK if name == "def_grass_wildmons" else SURF
                rate = parse_number(args[0])
                slots = []
            elif name == "db" and method is not None:
                slots.append((parse_number(args[0]), args[1]))
            elif name in ("end_grass_wildmons", "end_water_wildmons"):
                if rate > 0:
                    if len(slots) != len(self.wild_slot_chances):
                        raise ValueError(f"{map_name} : {len(slots)} emplacements au lieu de 10")
                    tables.append(
                        EncounterTable(
                            map_name=map_name,
                            method=method,
                            rate=rate,
                            slots=tuple(
                                Slot(species, level, chance * 100 / 256)
                                for (level, species), chance in zip(slots, self.wild_slot_chances, strict=True)
                            ),
                        )
                    )
                method = None
        return tables

    @cached_property
    def good_rod(self) -> list[tuple[str, int]]:
        result = []
        for line in self._lines("data/wild/good_rod.asm"):
            name, args = directive(line)
            if name == "db" and len(args) == 2:
                result.append((args[1], parse_number(args[0])))
        return result

    @cached_property
    def super_rod(self) -> list[EncounterTable]:
        if self.is_yellow:
            return self._super_rod_yellow()
        return self._super_rod_red_blue()

    def _super_rod_red_blue(self) -> list[EncounterTable]:
        # Rouge/Bleu : chaque carte pointe vers un groupe ; tirage uniforme dans le groupe.
        blocks = labelled_blocks(self._lines("data/wild/super_rod.asm"))
        groups: dict[str, list[tuple[str, int]]] = {}
        for label, lines in blocks.items():
            if "." not in label:
                continue
            mons = [directive(line)[1] for line in lines[1:]]
            groups[label.split(".")[1]] = [(args[1], parse_number(args[0])) for args in mons]
        tables = []
        for line in blocks["SuperRodData"]:
            name, args = directive(line)
            if name != "dbw":
                continue
            mons = groups[args[1].lstrip(".")]
            tables.append(
                EncounterTable(
                    map_name=args[0],
                    method=SUPER_ROD,
                    rate=None,
                    slots=tuple(Slot(species, level, 100 / len(mons)) for species, level in mons),
                )
            )
        return tables

    def _super_rod_yellow(self) -> list[EncounterTable]:
        # Jaune : 4 emplacements (espèce, niveau) par carte, probabilités fixes.
        tables = []
        for line in self._lines("data/wild/super_rod.asm"):
            name, args = directive(line)
            if name != "db" or len(args) != 9:
                continue
            pairs = list(zip(args[1::2], args[2::2], strict=True))
            tables.append(
                EncounterTable(
                    map_name=args[0],
                    method=SUPER_ROD,
                    rate=None,
                    slots=tuple(
                        Slot(species, parse_number(level), chance * 100 / 256)
                        for (species, level), chance in zip(pairs, YELLOW_SUPER_ROD_SLOT_CHANCES, strict=True)
                    ),
                )
            )
        return tables

    @cached_property
    def fishing_encounters(self) -> list[EncounterTable]:
        """Canne, Super Canne et Méga Canne. La Canne et la Super Canne sont utilisables
        sur toutes les cartes où la Méga Canne a des données."""
        tables = []
        old_species, old_level = OLD_ROD_ENCOUNTER
        good = tuple(Slot(species, level, 100 / len(self.good_rod)) for species, level in self.good_rod)
        for table in self.super_rod:
            tables.append(EncounterTable(table.map_name, OLD_ROD, None, (Slot(old_species, old_level, 100.0),)))
            tables.append(EncounterTable(table.map_name, GOOD_ROD, None, good))
            tables.append(table)
        return tables

    @cached_property
    def trades(self) -> list[Trade]:
        """Échanges en jeu, lus depuis les commentaires `; used in MAP`."""
        pattern = re.compile(r'npctrade\s+(\w+),\s*(\w+),\s*\w+,\s*"([^"]*)"\s*;\s*used in (\w+)')
        text = (self.root / "data/events/trades.asm").read_text(encoding="utf-8")
        return [Trade(map_name, give, get, nickname) for give, get, nickname, map_name in pattern.findall(text)]

    @cached_property
    def prizes(self) -> list[Prize]:
        """Pokémon du comptoir des lots du Casino de Céladopole (espèce, niveau, prix en jetons)."""
        blocks = labelled_blocks(self._lines("data/events/prizes.asm"))
        levels = {}
        for line in self._lines("data/events/prize_mon_levels.asm"):
            name, args = directive(line)
            if name == "db":
                levels[args[0]] = parse_number(args[1])
        result = []
        for group in ("Mon1", "Mon2"):
            species = [directive(line)[1][0] for line in blocks[f"PrizeMenu{group}Entries"] if line != 'db "@"']
            costs = [
                parse_number(directive(line)[1][0]) for line in blocks[f"PrizeMenu{group}Cost"] if line != 'db "@"'
            ]
            result += [Prize(s, levels[s], cost) for s, cost in zip(species, costs, strict=True)]
        return result

    @cached_property
    def map_names_by_label(self) -> dict[str, str]:
        """Nom de fichier de carte (ex. PowerPlant) -> constante (POWER_PLANT)."""
        result = {}
        for path in (self.root / "data/maps/headers").glob("*.asm"):
            for line in read_lines(path, self.defines):
                name, args = directive(line)
                if name == "map_header":
                    result[args[0]] = args[1]
        return result

    @cached_property
    def static_encounters(self) -> list[StaticEncounter]:
        """Pokémon fixes placés sur les cartes (`object_event ..., ESPÈCE, niveau`)."""
        counts: dict[tuple[str, str, int], int] = {}
        for path in sorted((self.root / "data/maps/objects").glob("*.asm")):
            map_name = self.map_names_by_label[path.stem]
            for line in read_lines(path, self.defines):
                name, args = directive(line)
                if name != "object_event" or len(args) < 8:
                    continue
                species, level = args[-2], args[-1]
                if species in self.dex_numbers and level.isdigit():
                    key = (map_name, species, int(level))
                    counts[key] = counts.get(key, 0) + 1
        return [StaticEncounter(m, s, lvl, n) for (m, s, lvl), n in counts.items()]


def _parse_base_stats(lines: list[str]) -> BaseStats:
    rows = [directive(line) for line in lines]
    db_rows = [args for name, args in rows if name == "db"]
    species = db_rows[0][0].removeprefix("DEX_")
    hp, attack, defense, speed, special = (parse_number(v) for v in db_rows[1])
    types = tuple(dict.fromkeys(db_rows[2]))  # type unique répété -> un seul type
    catch_rate = parse_number(db_rows[3][0])
    base_exp = parse_number(db_rows[4][0])
    start_moves = tuple(m for m in db_rows[5] if m != "NO_MOVE")
    growth_rate = db_rows[6][0].removeprefix("GROWTH_")

    # La liste tmhm peut s'étendre sur plusieurs lignes terminées par `\`.
    tmhm: list[str] = []
    collecting = False
    for line in lines:
        if line.startswith("tmhm"):
            collecting = True
            line = line.removeprefix("tmhm")
        if collecting:
            continued = line.endswith("\\")
            tmhm += split_args(line.rstrip("\\"))
            if not continued:
                break
    return BaseStats(
        species=species,
        hp=hp,
        attack=attack,
        defense=defense,
        speed=speed,
        special=special,
        types=types,
        catch_rate=catch_rate,
        base_exp=base_exp,
        start_moves=start_moves,
        growth_rate=growth_rate,
        tmhm=tuple(tmhm),
    )


def _parse_evos_moves(lines: list[str]) -> EvosMoves:
    evolutions: list[Evolution] = []
    learnset: list[tuple[int, str]] = []
    part = 0  # 0 = évolutions, 1 = attaques
    for line in lines:
        name, args = directive(line)
        if name != "db":
            continue
        if args == ["0"]:
            part += 1
            if part == 2:
                break
            continue
        if part == 0:
            kind = args[0]
            if kind == "EVOLVE_LEVEL":
                evolutions.append(Evolution("LEVEL", args[2], level=parse_number(args[1])))
            elif kind == "EVOLVE_ITEM":
                evolutions.append(Evolution("ITEM", args[3], item=args[1]))
            elif kind == "EVOLVE_TRADE":
                evolutions.append(Evolution("TRADE", args[2]))
            else:
                raise ValueError(f"Méthode d'évolution inconnue : {line}")
        else:
            learnset.append((parse_number(args[0]), args[1]))
    return EvosMoves(tuple(evolutions), tuple(learnset))

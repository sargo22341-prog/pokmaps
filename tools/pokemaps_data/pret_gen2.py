"""Lecture des désassemblages pret de la 2e génération (pokegold) : constantes, en-têtes de cartes, tilesets,
régions, données des Pokémon et sprites.

Seuls les fichiers sources texte (.asm), les blocs (.blk, .bin) et les images (.png) du dépôt sont lus : aucune
ROM n'est nécessaire. Les cartes sont lues dans `pret_gen2_maps.py`, les dresseurs dans `pret_gen2_trainers.py`,
les tilesets et collisions dans `pret_gen2_tilesets.py`, les scripts d'événements dans `pret_gen2_scripts.py` et
les offres des personnages dans `pret_gen2_offers.py`.

Unités (comme en 1re génération) : une carte fait `width` × `height` métatuiles ; une métatuile fait 4 × 4 tuiles
de 8 px (32 px) ; les coordonnées des événements sont en pas de 16 px, et chaque pas a sa propre collision.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

from .pret_gen2_offers import Gen2Offers
from .pret_gen2_scripts import ScriptFile
from .pret_gen2_tilesets import CollisionRules, Gen2Tileset, read_collision_rules, read_tilesets
from .pret_gen2_wild import headbutt_maps, rock_smash_maps
from .pret_source import annotated_lines, conditional_lines, macro_args, parse_int, source_lines

if TYPE_CHECKING:
    from .pret_models import PretMap, TrainerPokemon

# Environnements des villes et routes (data/maps/maps.asm) : les autres sont des intérieurs, grottes et donjons.
OUTDOOR_ENVIRONMENTS = frozenset({"TOWN", "ROUTE"})
# Régions renvoyées par RegionCheck (engine/overworld/landmarks.asm), nommées comme les cartes du monde.
JOHTO, KANTO = "JOHTO", "KANTO"
# Repères que RegionCheck range en Johto bien qu'ils suivent KANTO_LANDMARK : le M/S Aquaria, et tout ce qui
# vient à partir de la Route Victoire (Route 23, Plateau Indigo, Routes 26 à 28, Chutes Tohjo).
_FAST_SHIP, _VICTORY_ROAD = "LANDMARK_FAST_SHIP", "LANDMARK_VICTORY_ROAD"
# Palette des sprites de Pokémon : _GetSpritePalette (engine/overworld/overworld.asm) renvoie 0 pour eux.
POKEMON_SPRITE_PALETTE = "PAL_OW_RED"
# Repère des cartes spéciales, dont la région dépend de la carte d'où l'on vient.
_SPECIAL_LANDMARK = "LANDMARK_SPECIAL"


@dataclass(frozen=True)
class MapHeader:
    """En-tête d'une carte : constantes (map_constants.asm), en-tête (maps.asm) et attributs (attributes.asm)."""

    const: str
    label: str
    number: int  # rang de la carte dans map_constants.asm, à partir de 1 (unique dans le jeu)
    group: int  # groupe de cartes (newgroup), à partir de 1 : il choisit les toits
    width: int  # en métatuiles
    height: int
    tileset: str
    environment: str  # TOWN, ROUTE, INDOOR, CAVE, ENVIRONMENT_5, GATE ou DUNGEON
    landmark: str
    palette: str  # PALETTE_AUTO, PALETTE_DAY, PALETTE_NITE, PALETTE_MORN ou PALETTE_DARK
    fishing_group: str  # FISHGROUP_… : Pokémon pêchés dans l'eau de la carte (FISHGROUP_NONE : aucun)
    border_block: int

    @property
    def is_outdoor(self) -> bool:
        return self.environment in OUTDOOR_ENVIRONMENTS


@dataclass(frozen=True)
class OverworldSprite:
    """Image d'un sprite de personnage (première image : de face) et sa palette par défaut (PAL_OW_…)."""

    image: Path
    palette: str


class Gen2PretRepo:
    """Données d'un dépôt pret de la 2e génération extrait dans `root`.

    `versions` relie chaque version PokéAPI du jeu au symbole qui la distingue dans pret (games.Game.pret_versions) :
    les scripts sont lus version par version là où ils diffèrent (checkver)."""

    def __init__(self, root: Path, versions: tuple[tuple[str, str], ...]) -> None:
        if not versions:
            raise ValueError(f"{root.name} : aucune version à lire")
        self.root = root
        self.versions = versions

    def path(self, relative: str) -> Path:
        return self.root / relative

    def consts(self, relative: str, until: str | None = None) -> list[str]:
        """Constantes `const` d'un fichier dans l'ordre, jusqu'à la définition `until` (ex. NUM_TILESETS) si
        elle est donnée : une définition absente arrête la lecture."""
        result = []
        for line in source_lines(self.path(relative)):
            if until and line.startswith(f"DEF {until} "):
                return result
            if line.startswith("const "):
                result.append(line.split()[1])
        if until:
            raise ValueError(f"{self.root.name} : {until} introuvable dans {relative}")
        return result

    # --- Cartes -----------------------------------------------------------------

    @cached_property
    def headers(self) -> dict[str, MapHeader]:
        """Constante de carte -> en-tête complet."""
        sizes = self._map_sizes()
        attributes = self._map_attributes()
        result = {}
        for label, args in self._map_header_args().items():
            const, border = attributes[label]
            number, group, width, height = sizes[const]
            tileset, environment, landmark, palette, fishing = args[1], args[2], args[3], args[6], args[7]
            header = MapHeader(
                const, label, number, group, width, height, tileset, environment, landmark, palette, fishing, border
            )
            result[const] = header
        if missing := sorted(set(sizes) - result.keys()):
            raise ValueError(f"{self.root.name} : cartes sans en-tête dans data/maps/maps.asm : {missing}")
        return result

    def _map_sizes(self) -> dict[str, tuple[int, int, int, int]]:
        """Constante -> (rang global, groupe, largeur, hauteur), d'après les macros newgroup / map_const."""
        result: dict[str, tuple[int, int, int, int]] = {}
        group = 0
        for line in source_lines(self.path("constants/map_constants.asm")):
            if line.startswith("newgroup "):
                group += 1
            elif line.startswith("map_const "):
                const, width, height = macro_args(line, "map_const")
                result[const] = (len(result) + 1, group, int(width), int(height))
        if not result:
            raise ValueError(f"{self.root.name} : aucune carte dans constants/map_constants.asm")
        return result

    def _map_attributes(self) -> dict[str, tuple[str, int]]:
        """Label de carte -> (constante, métatuile de bordure)."""
        return {
            args[0]: (args[1], parse_int(args[2]))
            for args in (
                macro_args(line, "map_attributes")
                for line in source_lines(self.path("data/maps/attributes.asm"))
                if line.startswith("map_attributes ")
            )
        }

    def _map_header_args(self) -> dict[str, list[str]]:
        """Label de carte -> arguments de sa macro `map` (tileset, environnement, repère, musique…)."""
        return {
            args[0]: args
            for args in (
                macro_args(line, "map")
                for line in source_lines(self.path("data/maps/maps.asm"))
                if line.startswith("map ")
            )
        }

    @cached_property
    def maps(self) -> dict[str, PretMap]:
        from .pret_gen2_maps import read_maps

        return read_maps(self)

    @cached_property
    def script_files(self) -> dict[str, ScriptFile]:
        """Label de carte -> fichier de ses scripts et événements (data/maps/scripts.asm)."""
        result = {}
        include = re.compile(r'^INCLUDE "(maps/\w+\.asm)"$')
        for line in source_lines(self.path("data/maps/scripts.asm")):
            if match := include.match(line):
                script_file = ScriptFile(self.path(match.group(1)))
                for label in script_file.blocks:
                    if label.endswith("_MapEvents"):
                        result[label.removesuffix("_MapEvents")] = script_file
        return result

    @cached_property
    def block_files(self) -> dict[str, Path]:
        """Label de carte -> fichier .blk (plusieurs labels peuvent partager le même fichier)."""
        files: dict[str, Path] = {}
        pending: list[str] = []
        label_re = re.compile(r"^(\w+)_Blocks:")
        incbin_re = re.compile(r'INCBIN "([^"]+\.blk)"')
        for line in source_lines(self.path("data/maps/blocks.asm")):
            if label := label_re.match(line):
                pending.append(label.group(1))
            if incbin := incbin_re.search(line):
                files |= {name: self.path(incbin.group(1)) for name in pending}
                pending = []
        return files

    # --- Régions ----------------------------------------------------------------

    @cached_property
    def _landmark_order(self) -> tuple[list[str], int]:
        """Repères dans l'ordre, et rang du premier repère de Kanto (KANTO_LANDMARK)."""
        landmarks: list[str] = []
        kanto = None
        for line in source_lines(self.path("constants/landmark_constants.asm")):
            if line.startswith("const LANDMARK_"):
                landmarks.append(line.split()[1])
            elif line.startswith("DEF KANTO_LANDMARK "):
                kanto = len(landmarks)
        if kanto is None or _VICTORY_ROAD not in landmarks or _FAST_SHIP not in landmarks:
            raise ValueError(f"{self.root.name} : repères de RegionCheck introuvables")
        return landmarks, kanto

    def map_region(self, const: str) -> str | None:
        """Région de la carte d'après son repère, comme RegionCheck ; None pour une carte spéciale."""
        landmark = self.headers[const].landmark
        if landmark == _SPECIAL_LANDMARK:
            return None
        landmarks, kanto = self._landmark_order
        if landmark not in landmarks:
            raise ValueError(f"{self.root.name} : repère inconnu {landmark} pour {const}")
        index = landmarks.index(landmark)
        if landmark == _FAST_SHIP or index < kanto or index >= landmarks.index(_VICTORY_ROAD):
            return JOHTO
        return KANTO

    @cached_property
    def offers(self) -> Gen2Offers:
        """Offres des personnages et des installations, lues dans leurs scripts (pret_gen2_offers)."""
        return Gen2Offers(self)

    # --- Rencontres --------------------------------------------------------------

    @cached_property
    def headbutt_maps(self) -> frozenset[str]:
        """Cartes où Coup d'Boule fait tomber des Pokémon des arbres."""
        return headbutt_maps(self)

    @cached_property
    def rock_smash_maps(self) -> frozenset[str]:
        """Cartes où Éclate-Roc fait surgir des Pokémon des rochers."""
        return rock_smash_maps(self)

    # --- Tilesets ---------------------------------------------------------------

    @cached_property
    def tilesets(self) -> dict[str, Gen2Tileset]:
        return read_tilesets(self)

    @cached_property
    def collisions(self) -> CollisionRules:
        return read_collision_rules(self.root)

    # --- Pokémon ----------------------------------------------------------------

    @cached_property
    def species(self) -> list[str]:
        """Constantes des Pokémon dans l'ordre de leur numéro (index 0 = n° 1), jusqu'à NUM_POKEMON."""
        return self.consts("constants/pokemon_constants.asm", until="NUM_POKEMON")

    @cached_property
    def wild_held_items(self) -> dict[str, tuple[str, str]]:
        """Pokémon -> objets qu'il peut tenir à l'état sauvage (data/pokemon/base_stats, ligne « items »)."""
        result = {}
        species = set(self.species)
        for path in sorted(self.path("data/pokemon/base_stats").glob("*.asm")):
            lines = annotated_lines(path)
            names = [code.split()[1] for code, _ in lines if code.startswith("db ") and code.split()[1] in species]
            items = [macro_args(code, "db") for code, comment in lines if comment == "items"]
            if len(names) < 1 or len(items) != 1 or len(items[0]) != 2:
                raise ValueError(f"{path.name} : Pokémon ou objets tenus introuvables")
            result[names[0]] = (items[0][0], items[0][1])
        if missing := sorted(species - result.keys()):
            raise ValueError(f"{self.root.name} : Pokémon sans données de base : {missing}")
        return result

    @cached_property
    def happiness_to_evolve(self) -> int:
        """Bonheur à partir duquel un Pokémon évolue par bonheur (HAPPINESS_TO_EVOLVE)."""
        values = [
            parse_int(line.split()[-1])
            for line in source_lines(self.path("constants/pokemon_data_constants.asm"))
            if line.startswith("DEF HAPPINESS_TO_EVOLVE ")
        ]
        if len(values) != 1:
            raise ValueError(f"{self.root.name} : HAPPINESS_TO_EVOLVE introuvable")
        return values[0]

    @cached_property
    def learnsets(self) -> dict[str, list[tuple[int, str]]]:
        """Pokémon -> attaques apprises par niveau, dans l'ordre (data/pokemon/evos_attacks.asm)."""
        pointers = [
            macro_args(line, "dw")[0]
            for line in source_lines(self.path("data/pokemon/evos_attacks_pointers.asm"))
            if line.startswith("dw ")
        ]
        by_label = dict(zip(pointers, self.species, strict=True))
        result: dict[str, list[tuple[int, str]]] = {}
        current = None
        zeros = 0
        for line in source_lines(self.path("data/pokemon/evos_attacks.asm")):
            if line.endswith(":") and line[:-1] in by_label:
                current, zeros = by_label[line[:-1]], 0
                result[current] = []
            elif current and line.startswith("db "):
                args = macro_args(line, "db")
                if args == ["0"]:
                    zeros += 1
                    current = None if zeros == 2 else current
                elif zeros == 1:
                    result[current].append((parse_int(args[0]), args[1]))
        return result

    @cached_property
    def trainer_parties(self) -> dict[tuple[str, int], list[TrainerPokemon]]:
        from .pret_gen2_trainers import read_trainer_parties

        return read_trainer_parties(self)

    @cached_property
    def machines(self) -> dict[str, str]:
        """Constante d'objet CT/CS (ex. TM_DYNAMICPUNCH) -> identifiant PokéAPI (tm01)."""
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

    def checkver(self, version_symbol: str) -> bool:
        """Valeur de la commande de script checkver dans cette version (GS_VERSION : 0 en Or, 1 en Argent)."""
        return self._checkver[version_symbol]

    @cached_property
    def _checkver(self) -> dict[str, bool]:
        result = {}
        for _, symbol in self.versions:
            values = [
                parse_int(line.split()[-1])
                for line in conditional_lines(self.path("constants/misc_constants.asm"), frozenset({symbol}))
                if line.startswith("DEF GS_VERSION ")
            ]
            if len(values) != 1:
                raise ValueError(f"{self.root.name} : GS_VERSION introuvable pour {symbol}")
            result[symbol] = values[0] != 0
        return result

    @cached_property
    def trainer_ids(self) -> dict[str, list[str]]:
        """Classe de dresseur -> constantes de ses dresseurs, dans l'ordre de leurs équipes (const_def 1)."""
        result: dict[str, list[str]] = {}
        current = None
        for line in source_lines(self.path("constants/trainer_constants.asm")):
            if line.startswith("trainerclass "):
                current = line.split()[1]
                result[current] = []
            elif line.startswith("const ") and current:
                result[current].append(line.split()[1])
        return result

    # --- Sprites ----------------------------------------------------------------

    @cached_property
    def sprites(self) -> dict[str, OverworldSprite]:
        """Sprite de personnage (SPRITE_YOUNGSTER…) ou de Pokémon (SPRITE_SNORLAX…) -> image et palette."""
        consts = self.consts("constants/sprite_constants.asm", until="NUM_POKEMON_SPRITES")
        images = {
            label: self.path(path.replace(".2bpp", ".png"))
            for label, path in self._labelled_files_inline("gfx/sprites.asm").items()
        }
        overworld = [
            macro_args(line, "overworld_sprite")
            for line in source_lines(self.path("data/sprites/sprites.asm"))
            if line.startswith("overworld_sprite ")
        ]
        # SPRITE_NONE (0) n'a pas d'image : la table commence à SPRITE_CHRIS.
        result = {
            const: OverworldSprite(images[args[0]], args[3])
            for const, args in zip(consts[1 : len(overworld) + 1], overworld, strict=True)
        }
        return result | self._pokemon_sprites(consts)

    def _pokemon_sprites(self, consts: list[str]) -> dict[str, OverworldSprite]:
        """Sprites de Pokémon (SPRITE_UNOWN…) : l'icône du menu de l'espèce, d'après data/sprites/sprite_mons.asm."""
        first = consts.index("SPRITE_UNOWN")
        mons = [
            line.split()[1]
            for line in source_lines(self.path("data/sprites/sprite_mons.asm"))
            if line.startswith("db ")
        ]
        icons = [
            line.split()[1] for line in source_lines(self.path("data/pokemon/menu_icons.asm")) if line.startswith("db ")
        ]
        icon_of = dict(zip(self.species, icons, strict=False))
        icon_consts = self.consts("constants/icon_constants.asm", until="NUM_ICONS")
        pointers = [
            macro_args(line, "dw")[0]
            for line in source_lines(self.path("data/icon_pointers.asm"))
            if line.startswith("dw ")
        ]
        icon_labels = dict(zip(icon_consts, pointers, strict=True))
        files = self._labelled_files_inline("gfx/icons.asm")
        return {
            consts[first + index]: OverworldSprite(
                self.path(files[icon_labels[icon_of[mon]]].replace(".2bpp", ".png")), POKEMON_SPRITE_PALETTE
            )
            for index, mon in enumerate(mons)
        }

    def _labelled_files_inline(self, relative: str) -> dict[str, str]:
        """Label -> fichier, pour les fichiers où le label et son INCBIN sont sur la même ligne."""
        pattern = re.compile(r'^(\w+)::?\s*INCBIN "([^"]+)"$')
        return {
            match.group(1): match.group(2)
            for line in source_lines(self.path(relative))
            if (match := pattern.match(line))
        }

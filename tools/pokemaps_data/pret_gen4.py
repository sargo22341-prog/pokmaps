"""Façade des sources pret DS : Platine (sources lisibles) et Diamant/Perle (fichiers extraits et moteur en C ou
en assembleur). Chaque propriété lit une seule fois sa partie du dépôt et rend des données pures du même modèle
pour les deux variantes ; le rendu, les rencontres et les offres sont construits par les phases suivantes.
"""

from __future__ import annotations

from functools import cached_property
from pathlib import Path

from .pret_gen4_encounter_tables import EncounterTable, read_dp_encounters, read_platinum_encounters
from .pret_gen4_events import read_events
from .pret_gen4_flow import PlatinumContext, ScriptFlow, diamond_pearl_flow, platinum_flow, read_platinum_macros
from .pret_gen4_flow_values import CommonScripts
from .pret_gen4_land import LandBlock, read_land_block
from .pret_gen4_map_models import CameraSettings, Gen4Area, Gen4Events, Gen4Header, Gen4Matrix, LightingPeriod
from .pret_gen4_maps import (
    PlatinumNames,
    read_areas,
    read_cameras,
    read_headers,
    read_lighting,
    read_matrices,
    read_prop_sets,
)
from .pret_gen4_maps_dp import read_dp_cameras, read_dp_headers, read_dp_lighting
from .pret_gen4_moves import read_gen4_moves
from .pret_gen4_narc import FIELD_DATA, members, read_dp_areas, read_dp_events, read_dp_matrices, read_dp_prop_sets
from .pret_gen4_nitro import NitroFile, read_nsbmd
from .pret_gen4_rematches import VsSeekerRules, read_vs_seeker
from .pret_gen4_script_binary import InitScripts, ScriptFile, read_init_scripts, read_script_file
from .pret_gen4_script_commands import ScriptCommand, read_command_table
from .pret_gen4_script_ids import ScriptIds, read_script_ids
from .pret_gen4_script_ranges import ScriptRanges, read_script_ranges
from .pret_gen4_scripts import FIELD_MACROS, TextScriptFile, read_frontier_scripts, read_macros, read_platinum_scripts
from .pret_gen4_source import c_enum, included_defines, metang_enum, read_binary
from .pret_gen4_textures import NitroTextures, read_nsbtx
from .pret_gen4_trainers import Gen4Trainer, read_trainers
from .pret_moves import PretMove

_VARIANTS = {frozenset({"PLATINUM"}): "platinum", frozenset({"DIAMOND", "PEARL"}): "diamond-pearl"}
_MARKERS = {"platinum": "res/field/maps/data", "diamond-pearl": f"{FIELD_DATA}/land_data/land_data_release"}
_SCRIPTS = f"{FIELD_DATA}/script/scr_seq_release"
# Énumérations de Platine dont les scripts du terrain emploient les noms comme arguments.
_SCRIPT_ENUMS = (
    "vars_flags",
    "trainers",
    "items",
    "species",
    "moves",
    "time_of_day",
    "days_of_week",
    "genders",
    "badges",
    "movement_types",
    "object_events_gfx",
    "map_headers",
    "mart_specialties_id",
    "mart_decor_id",
    "mart_seal_id",
    "mart_frontier_id",
    "tutor_locations",
    "battle_tower_modes",
)


class Gen4PretRepo:
    def __init__(self, root: Path, versions: tuple[tuple[str, str], ...]) -> None:
        symbols = frozenset(symbol for _, symbol in versions)
        if symbols not in _VARIANTS or any(version != symbol.lower() for version, symbol in versions):
            raise ValueError(f"{root} : versions DS invalides : {versions}")
        self.variant = _VARIANTS[symbols]
        if not (root / _MARKERS[self.variant]).is_dir():
            raise ValueError(f"{root} : dépôt {self.variant} attendu ({_MARKERS[self.variant]} absent)")
        self.root = root
        self.versions = versions
        self.platinum = self.variant == "platinum"
        self._blocks: dict[int, LandBlock] = {}

    @cached_property
    def names(self) -> PlatinumNames:
        if not self.platinum:
            raise ValueError(f"{self.root} : les listes d'archives nommées n'existent qu'en Platine")
        return PlatinumNames(self.root)

    @cached_property
    def headers(self) -> dict[int, Gen4Header]:
        return read_headers(self.root, self.names) if self.platinum else read_dp_headers(self.root)

    @cached_property
    def matrices(self) -> dict[int, Gen4Matrix]:
        return read_matrices(self.root, self.names) if self.platinum else read_dp_matrices(self.root)

    @cached_property
    def events(self) -> dict[int, Gen4Events]:
        return read_events(self.root, self.names) if self.platinum else read_dp_events(self.root)

    @cached_property
    def areas(self) -> dict[int, Gen4Area]:
        return read_areas(self.root, self.names) if self.platinum else read_dp_areas(self.root)

    @cached_property
    def prop_sets(self) -> dict[int, tuple[int, ...]]:
        return read_prop_sets(self.root, self.names) if self.platinum else read_dp_prop_sets(self.root)

    @cached_property
    def lighting(self) -> dict[int, tuple[LightingPeriod, ...]]:
        return read_lighting(self.root, self.names) if self.platinum else read_dp_lighting(self.root)

    @cached_property
    def cameras(self) -> tuple[CameraSettings, ...]:
        return read_cameras(self.root) if self.platinum else read_dp_cameras(self.root)

    @cached_property
    def encounters(self) -> dict[str, dict[int, EncounterTable]]:
        """Tables de rencontres par version puis par numéro (celui des en-têtes)."""
        if self.platinum:
            return {"platinum": read_platinum_encounters(self.root, self.names.archives["encounters"])}
        return read_dp_encounters(self.root)

    @cached_property
    def moves(self) -> list[PretMove]:
        return read_gen4_moves(self.root)

    def land_block(self, index: int) -> LandBlock:
        """Bloc de terrain `index` (numéro des matrices), lu à la première demande."""
        if index not in self._blocks:
            self._blocks[index] = read_land_block(self._block_paths[index], diamond_pearl=not self.platinum)
        return self._blocks[index]

    @cached_property
    def _block_paths(self) -> dict[int, Path]:
        if self.platinum:
            order = self.names.order("res/field/maps/data/map_data.order")
            return {index: self.root / "res/field/maps/data" / name for name, index in order.items()}
        return members(self.root / _MARKERS[self.variant])

    def map_textures(self, index: int) -> NitroTextures:
        """Jeu de textures de terrain `index` (Gen4Area.texture_set)."""
        return self._textures("maps/texture_sets", "map_texture_sets", "areadata/area_map_tex/map_tex_set", index)

    def prop_textures(self, index: int) -> NitroTextures:
        """Textures des objets posés du jeu `index` (même numéro que Gen4Area.prop_set)."""
        return self._textures(
            "props/texture_sets", "prop_texture_sets", "areadata/area_build_model/areabm_texset", index
        )

    def _textures(self, platinum: str, order: str, diamond_pearl: str, index: int) -> NitroTextures:
        if self.platinum:
            names = {i: n for n, i in self.names.order(f"res/field/{platinum}/{order}.order").items()}
            path = self.root / "res/field" / platinum / names[index]
            path = path if path.suffix else path.with_suffix(".nsbtx")
        else:
            path = members(self.root / FIELD_DATA / diamond_pearl)[index]
        return read_nsbtx(read_binary(path), str(path))

    def prop_model(self, index: int) -> NitroFile:
        """Modèle d'objet posé `index` (valeurs des jeux d'objets)."""
        if self.platinum:
            names = {i: n for n, i in self.names.order("res/field/props/models/map_prop_models.order").items()}
            path = self.root / "res/field/props/models" / names[index]
        else:
            path = members(self.root / FIELD_DATA / "build_model/build_model")[index]
        return read_nsbmd(read_binary(path), str(path))

    @cached_property
    def script_commands(self) -> tuple[ScriptCommand, ...]:
        if self.platinum:
            raise ValueError(f"{self.root} : Platine décrit ses scripts en macros, sans table binaire")
        return read_command_table(self.root)

    @cached_property
    def scripts(self) -> dict[int, ScriptFile | TextScriptFile]:
        """Fichiers de scripts désignés par les en-têtes ou appelés par numéro, hors initialisation."""
        if self.platinum:
            return dict(read_platinum_scripts(self.root, self.names.archives["scripts"]))
        return dict(self._dp_scripts[0])

    @cached_property
    def init_scripts(self) -> dict[int, InitScripts]:
        """Scripts d'initialisation de Diamant/Perle (ceux de Platine sont des fichiers .s comme les autres)."""
        if self.platinum:
            raise ValueError(f"{self.root} : les scripts d'initialisation de Platine sont lus avec les scripts")
        return self._dp_scripts[1]

    @cached_property
    def _dp_scripts(self) -> tuple[dict[int, ScriptFile], dict[int, InitScripts]]:
        """Chaque fichier a la forme que lui donnent les en-têtes. Un fichier qu'aucun en-tête ne désigne est lu
        comme scripts (scripts communs appelés par numéro), sinon comme table d'initialisation d'un lieu
        inutilisé ; un fichier vide est écarté, un fichier illisible des deux façons arrête la lecture."""
        initial = {header.init_scripts for header in self.headers.values()}
        scripts: dict[int, ScriptFile] = {}
        tables: dict[int, InitScripts] = {}
        for index, path in members(self.root / _SCRIPTS).items():
            if index in initial:
                tables[index] = read_init_scripts(path)
            elif path.stat().st_size:
                try:
                    scripts[index] = read_script_file(path, self.script_commands)
                except ValueError as script_error:
                    if index in {header.scripts for header in self.headers.values()}:
                        raise
                    tables[index] = _init_or_fail(path, script_error)
        return scripts, tables

    @cached_property
    def constants(self) -> dict[str, int]:
        """Constantes nommées de Platine lues par les scripts (énumérations generated/*.txt, `#define` entiers des
        en-têtes constants/ qu'incluent les macros) ; un nom défini deux fois avec deux valeurs différentes est
        écarté, et reste alors un texte que les lectures refusent si besoin."""
        values: dict[str, int] = {"TRUE": 1, "FALSE": 0}
        conflicts: set[str] = set()
        sources = [metang_enum(self.root / f"generated/{enum}.txt") for enum in _SCRIPT_ENUMS]
        sources.append(c_enum(self.root / "include/constants/npc_trades.h", "NPCTradeID"))
        for source in (*sources, included_defines(self.root, (*FIELD_MACROS, "include/constants/contests.h"))):
            for name, value in source.items():
                if values.get(name, value) != value:
                    conflicts.add(name)
                values[name] = value
        return {name: value for name, value in values.items() if name not in conflicts}

    @cached_property
    def flows(self) -> dict[int, ScriptFlow]:
        """Flux de chaque fichier de scripts du terrain, sous la forme commune aux deux jeux (pret_gen4_flow)."""
        if not self.platinum:
            return {
                index: diamond_pearl_flow(f"scripts {index}", script, self.script_commands)
                for index, script in self._dp_scripts[0].items()
            }
        context = PlatinumContext(
            *read_platinum_macros(self.root),
            frozenset(read_macros(self.root, ("asm/macros/movement.inc",))),
            self.constants,
        )
        return {
            index: platinum_flow(script, context)
            for index, script in self.scripts.items()
            if isinstance(script, TextScriptFile)
        }

    @cached_property
    def trainers(self) -> dict[int, Gen4Trainer]:
        return read_trainers(self.root, self._repo_name)

    @cached_property
    def vs_seeker(self) -> VsSeekerRules:
        return read_vs_seeker(self.root, self._repo_name, self.names.trainers if self.platinum else None)

    @property
    def _repo_name(self) -> str:
        return "pokeplatinum" if self.platinum else "pokediamond"

    @cached_property
    def script_ids(self) -> ScriptIds:
        return read_script_ids(self.root, self._repo_name, self.names.archives["scripts"] if self.platinum else None)

    @cached_property
    def script_ranges(self) -> ScriptRanges:
        return read_script_ranges(self.root, self.names.archives["scripts"] if self.platinum else None)

    @cached_property
    def common_scripts(self) -> CommonScripts:
        return CommonScripts(self.flows[self.script_ids.common_file], self.script_ids.common)

    @cached_property
    def frontier_scripts(self) -> dict[str, TextScriptFile]:
        if not self.platinum:
            raise ValueError(f"{self.root} : les scripts du Frontier n'existent qu'en Platine")
        return read_frontier_scripts(self.root)


def _init_or_fail(path: Path, script_error: ValueError) -> InitScripts:
    try:
        return read_init_scripts(path)
    except ValueError as init_error:
        raise ValueError(f"{path} : ni scripts ({script_error}) ni initialisation ({init_error})") from init_error

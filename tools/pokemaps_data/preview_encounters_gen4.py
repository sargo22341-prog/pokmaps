"""Correction bornée du fixe oublié par PokéAPI, avant le lecteur général des scripts DS."""

from __future__ import annotations

import struct
from typing import TYPE_CHECKING

from .builder_encounters import EncounterGroup
from .games import PretFormat

if TYPE_CHECKING:
    from .builder import DatabaseBuilder


def complete_preview_encounters(builder: DatabaseBuilder) -> None:
    for game, vg in zip(builder.games, builder.vg_ids, strict=True):
        if game.pret_format is not PretFormat.GEN4 or game.pret_repo != "pokediamond":
            continue
        root = builder.pret_root(game, "le combat de Giratina")
        path = root / "files/fielddata/script/scr_seq_release/narc_0283.bin"
        if path.stat().st_size != 312:
            raise ValueError(f"{path} : script de Giratina modifié")
        # map_header.c : MAP_TURNBACK_CAVE_GIRATINA_ROOM -> script 283.
        # scrcmd.c : ScrCmd_LegendaryBattle (02BD), puis deux paramètres u16 (espèce, niveau).
        command, species, level = struct.unpack_from("<HHH", path.read_bytes(), 93)
        if (command, species, level) != (0x2BD, 487, 70):
            raise ValueError(f"{path}:93 : combat de Giratina non reconnu")
        methods = {r["identifier"]: int(r["id"]) for r in builder.api.table("encounter_methods")}
        area = builder.locations.area_ids["turnback-cave/after-pillar-3"]
        groups = builder.encounters.encounter_groups
        for version in (r for r in builder.version_rows if int(r["version_group_id"]) == vg):
            version_id = int(version["id"])
            if any(g.version_id == version_id and g.pokemon_id == species for g in groups):
                continue
            groups.append(EncounterGroup(version_id, area, species, methods["static"], (), level, level, None, 1))

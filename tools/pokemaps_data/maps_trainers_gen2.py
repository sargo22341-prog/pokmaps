"""Équipes de revanche et objets tenus des dresseurs de Johto."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .maps_layout import identifier
from .pret_identifiers import item_identifier, species_identifier
from .pret_source import macro_args

if TYPE_CHECKING:
    from .maps_characters import ObjectRow
    from .pret_gen2 import Gen2PretRepo
    from .pret_models import MapObject


def attach_teams(repo: Gen2PretRepo, label: str, obj: MapObject, row: ObjectRow) -> None:
    """Conserve une seule icône avec toutes ses équipes et leurs objets tenus."""
    trainer_class = obj.trainer_class
    if trainer_class is None:
        return
    numbers = [variant.number for variant in obj.trainer_variants]
    if obj.trainer_number is not None:
        numbers = [obj.trainer_number]
        source = repo.script_files[label]
        lines = source.reachable_lines(obj.text, checkver=None) if obj.text and source.has_label(obj.text) else []
        ids = repo.trainer_ids[trainer_class]
        rematches = {
            ids.index(args[1]) + 1
            for line in lines
            if line.startswith("loadtrainer ") and (args := macro_args(line, "loadtrainer"))[0] == trainer_class
        }
        for number in sorted(rematches - set(numbers)):
            row.rematches.append(
                [
                    (species_identifier(mon.species), mon.level, tuple(identifier(move) for move in mon.moves))
                    for mon in repo.trainer_parties[trainer_class, number]
                ]
            )
            numbers.append(number)
    for team, number in enumerate(numbers, start=1):
        for slot, mon in enumerate(repo.trainer_parties[trainer_class, number], start=1):
            if mon.item:
                row.held_items[team, slot] = item_identifier(mon.item, repo.machines)

"""Provenance des événements HGSS non décrits par les rencontres PokéAPI."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .builder import DatabaseBuilder
    from .builder_encounters import EncounterGroup


def complete(builder: DatabaseBuilder, groups: list[EncounterGroup]) -> None:
    if not any(game.pret_repo == "pokeheartgold" for game in builder.games):
        return
    from .builder_encounters import EncounterGroup

    method = next(int(row["id"]) for row in builder.encounters.method_values if row["identifier"] == "gift")
    for version in (15, 16):
        groups.append(
            EncounterGroup(
                version,
                30_117,
                172,
                method,
                (),
                30,
                30,
                None,
                1,
                [
                    "Événement externe : présenter le Pichu distribué au Bois aux Chênes. "
                    "Pichu Troizépi, forme spéciale non chromatique, sans évolution ni échange possible."
                ],
                external_event=True,
            )
        )

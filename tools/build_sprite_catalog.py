"""Régénère le tableau de toutes les espèces depuis les CSV PokéAPI épinglés."""

from pathlib import Path

from pokemaps_data.pokeapi import PokeApi
from pokemaps_data.sources import fetch_pokeapi_csv
from pokemaps_data.sprite_catalog import write_sprite_catalog


def main() -> None:
    root = Path(__file__).resolve().parent
    api = PokeApi(fetch_pokeapi_csv(root / ".cache"))
    write_sprite_catalog(api, root.parent / "docs/donnees/sprites-pokemon.md")


if __name__ == "__main__":
    main()

"""Produit les planches de relecture DS dans le scratchpad, sans modifier les cartes."""

import argparse
from pathlib import Path

from pokemaps_data.games import GEN4_GAMES
from pokemaps_data.maps_review_gen4 import write_review, write_sprite_review


def main() -> None:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", type=Path, default=root / "build/preview/sinnoh-maps")
    parser.add_argument("--output", type=Path, default=root / "build/scratchpad/gen4-map-review")
    args = parser.parse_args()
    for game in GEN4_GAMES:
        sheets = write_review(args.maps / game.version_group, args.output)
        write_sprite_review(args.maps / game.version_group, args.output)
        print(f"{game.version_group} : {len(sheets)} planches dans {args.output}")


if __name__ == "__main__":
    main()

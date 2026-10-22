"""Produit les planches de l'atlas HGSS dans le scratchpad, sans modifier l'aperçu."""

import argparse
from pathlib import Path

from pokemaps_data.maps_review_hgss import write_johto_review


def main() -> None:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", type=Path, default=root / "build/preview/hgss-maps/atlas")
    parser.add_argument("--output", type=Path, default=root / "build/scratchpad/hgss-map-review")
    args = parser.parse_args()
    sheets = write_johto_review(args.maps, args.output)
    print(f"HGSS : {len(sheets)} planches et leur index dans {args.output}")


if __name__ == "__main__":
    main()

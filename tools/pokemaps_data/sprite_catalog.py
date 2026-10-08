"""Catalogue de provenance, pour toutes les espèces de la source épinglée."""

from pathlib import Path

from .pokeapi import PokeApi
from .sources import POKEAPI_COMMIT, POKEAPI_SPRITES_COMMIT, POKEAPI_SPRITES_URL
from .sprites import ANIMATED_SPRITES, LAST_ANIMATED_SPECIES, SHINY_SPRITES


def sprite_catalog(api: PokeApi) -> str:
    """Décrit les sources existantes sans inventer de fournisseur pour les générations futures."""
    names = {
        int(row["pokemon_species_id"]): row["name"]
        for row in api.table("pokemon_species_names")
        if row["local_language_id"] == "5"
    }
    rows = sorted(api.table("pokemon_species"), key=lambda row: int(row["id"]))
    lines = [
        "# Provenance des sprites Pokémon",
        "",
        f"Catalogue : {len(rows)} espèces, export PokéAPI `{POKEAPI_COMMIT}`.",
        "",
        f"Images : PokeAPI/sprites, commit `{POKEAPI_SPRITES_COMMIT}`.",
        "",
        "Les espèces 1 à 251 sont embarquées. De 252 à 649, les chemins décrivent la source prévue,",
        "sans affirmer que les images sont embarquées. Après 649, aucune source n'est configurée ;",
        "le pipeline refuse un jeu qui en aurait besoin. Les fixes sont la première image du GIF",
        "normal ou chromatique, encodée en WebP sans perte, comme les animations.",
        "",
        "Zarbi : `201-a.gif` à `201-z.gif`, `201-exclamation.gif` et `201-question.gif`, dans les mêmes",
        "dossiers normal/chromatique. Les quatre variantes sont dans `sprites/unown/`.",
        "",
        "Régénération : `python tools/build_sprite_catalog.py` après préparation des sources.",
        "",
        "| N° | Pokémon | Génération | Normal fixe | Normal animé | Chromatique fixe | Chromatique animé |",
        "|---:|---|---:|---|---|---|---|",
    ]
    for row in rows:
        species = int(row["id"])
        if species not in names:
            raise ValueError(f"Nom français absent du catalogue : Pokémon {species}")
        if species <= LAST_ANIMATED_SPECIES:
            normal = _link(ANIMATED_SPRITES, species)
            shiny = _link(SHINY_SPRITES, species)
            cells = (f"Première image de {normal}", normal, f"Première image de {shiny}", shiny)
        else:
            cells = ("Non configuré",) * 4
        lines.append(f"| {species} | {names[species]} | {row['generation_id']} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def write_sprite_catalog(api: PokeApi, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(sprite_catalog(api), encoding="utf-8")


def _link(pattern: str, species: int) -> str:
    url = POKEAPI_SPRITES_URL.format(commit=POKEAPI_SPRITES_COMMIT, path=pattern.format(id=species))
    return f"[GIF Noir/Blanc]({url})"

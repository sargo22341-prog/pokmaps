"""Aperçu des guides HGSS, construit et vérifié avant remplacement atomique."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from .activities_hgss import activity_catalog
from .catalog_pokemon_hgss import pokemon_catalog
from .guides_hgss import guide_catalog, map_entries, weekly_calendar
from .objectives_hgss import breeding_roots, objective_catalog
from .pokeapi import PokeApi
from .pret_gen4_source import c_defines, read_json
from .pret_hgss_pokemon import read_hgss_pokemon
from .preview_characters_hgss import check_characters
from .preview_pokemon_hgss import _replace_preview, validate_sources
from .preview_wild_hgss import check_encounters_preview
from .sources import DATA_DIR, HGSS_PRET_COMMIT, POKEAPI_COMMIT, PREVIEW_DIR, fetch_pokeapi_csv
from .sources_characters_hgss import source_digest
from .validate_content_hgss import validate_content

CONTRACT = Path(__file__).resolve().parents[2] / "docs/generations/contenus-hgss-sources.json"


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def recipe() -> dict[str, str]:
    names = (
        "preview_content_hgss.py",
        "guides_hgss.py",
        "objectives_hgss.py",
        "activities_hgss.py",
        "pokewalker_hgss.py",
        "validate_content_hgss.py",
        "review_content_hgss.py",
        "catalog_pokemon_hgss.py",
        "pret_hgss_pokemon.py",
        "evolution_hgss.py",
        "pokeapi.py",
        "pret_gen4_source.py",
    )
    return {name: source_digest(Path(__file__).with_name(name)) for name in names} | {
        f"data/{name}": source_digest(DATA_DIR / name)
        for name in (
            "hgss_guides.json",
            "hgss_activities.json",
            "hgss_calendar.json",
            "hgss_maps.csv",
            "hgss_pokemon_rules.json",
        )
    }


def build_content(cache: Path, output: Path) -> None:
    _validate_target(cache, output)
    root = cache / "hgss-qualification"
    sources = read_json(CONTRACT)
    if sources["commit"] != HGSS_PRET_COMMIT or sources["pokeapi_commit"] != POKEAPI_COMMIT:
        raise ValueError("HGSS : provenance des contenus incorrecte")
    for name, expected in sources["native"].items():
        if source_digest(root / name) != expected:
            raise ValueError(f"HGSS : source de contenu modifiée : {name}")
    characters = check_characters(output / "hgss-characters")
    check_encounters_preview(output / "hgss-encounters")
    encounters = json.loads((output / "hgss-encounters/encounters.json").read_text(encoding="utf-8"))
    api_root = fetch_pokeapi_csv(cache)
    validate_sources(root, api_root)
    api = PokeApi(api_root)
    pokemon = pokemon_catalog(read_hgss_pokemon(root), api, read_json(DATA_DIR / "hgss_pokemon_rules.json"), [])
    species = c_defines(root / "include/constants/species.h", "SPECIES_")
    content = dict(
        schema=1,
        commit=HGSS_PRET_COMMIT,
        versions=["heartgold", "soulsilver"],
        status="preparatory",
        recipe=recipe(),
        sources=sources,
        prerequisites={
            name: source_digest(output / name)
            for name in ("hgss-characters/inventory.json", "hgss-encounters/inventory.json")
        },
        guides=guide_catalog(characters, map_entries()),
        objectives=objective_catalog(encounters, pokemon, species, breeding_roots(api), _local_trades(characters)),
        calendar=characters["calendar"],
        weekly=weekly_calendar(characters),
        activities=activity_catalog(root, characters, encounters),
        names_fr={str(row["id"]): row["name_fr"] for row in pokemon["pokemon"]},
        item_names_fr=characters["names"]["items"],
        objective_rules=_objective_rules(),
    )
    validate_content(content)
    from .review_content_hgss import write_review

    with TemporaryDirectory(prefix=".hgss-content-", dir=output) as temporary:
        staging = Path(temporary) / "staging"
        staging.mkdir()
        _write(staging / "content.json", content)
        write_review(staging, content)
        _write(staging / "inventory.json", {p.name: source_digest(p) for p in sorted(staging.iterdir())})
        check_content(staging, output)
        _replace_preview(staging, output / "hgss-content", Path(temporary) / "previous")
    if output.resolve() == PREVIEW_DIR.resolve():
        _snapshot(content)
    print(f"HGSS : {len(content['guides'])} guides, 54 objectifs et 13 activités validés")


def _validate_target(cache: Path, output: Path) -> None:
    target = (output / "hgss-content").resolve()
    assets = Path(__file__).resolve().parents[2] / "app/src/main/assets"
    if any(target.is_relative_to(p) or p.is_relative_to(target) for p in (cache.resolve(), assets.resolve())):
        raise ValueError("HGSS : les contenus doivent rester séparés des sources et des assets distribués")


def _snapshot(content: dict) -> None:
    path = CONTRACT.with_name("contenus-hgss-catalogue.json")
    _write(path, content)
    _write(
        CONTRACT.with_name("contenus-hgss-preuve.json"),
        dict(
            catalog_sha256=source_digest(path),
            guides=len(content["guides"]),
            objectives=len(content["objectives"]),
            activities=len(content["activities"]["guides"]),
        ),
    )


def _local_trades(characters: dict) -> list[dict]:
    active = {row["values"][0] for row in characters["service_steps"] if row["command"] == "LoadNPCTrade"}
    return [row for row in characters["trades"] if row["index"] in active]


def _objective_rules() -> dict:
    return dict(
        scope_fr="Collection réalisable sur une sauvegarde jusqu’à l’après-Red, sans autre cartouche, accessoire "
        "ni distribution. Les échanges internes avec les PNJ restent autorisés. Les rencontres conditionnelles "
        "(radio, essaims, Safari, horaires) ne sont pas toutes disponibles simultanément.",
        choices_fr="Un starter de Johto, un de Kanto et un de Hoenn : 27 configurations par cartouche. "
        "Ne jamais additionner les listes des configurations pour former un objectif.",
        fossils_fr="HeartGold : Amonita, Anorith et Ptéra ; SoulSilver : Kabuto, Lilia et Ptéra. "
        "Les autres fossiles acceptés par le musée sont importés.",
        exclusions_fr=[
            "Autres choix de starters et leurs évolutions, sauf provenance locale indépendante.",
            "Évolutions par échange ou lieu absent ; beauté préparée dans un autre jeu.",
            "Pokéwalker, Parc des Amis, échanges externes, distributions et événements externes.",
            "Rayquaza exige les deux légendes HGSS ; Kyogre est local à HeartGold, Groudon à SoulSilver.",
            "Latias erre dans HeartGold ; Latios erre dans SoulSilver. L’autre demande le Mystécristal.",
        ],
        sources=["src/field/rock_smash_item.c", "src/scrcmd_fossils.c", "src/get_egg.c"],
    )


def check_content(folder: Path, prerequisites: Path | None = None) -> dict:
    inventory = read_json(folder / "inventory.json")
    actual = {p.name: source_digest(p) for p in folder.iterdir() if p.is_file() and p.name != "inventory.json"}
    if inventory != actual or set(actual) != {"content.json", "index.html"}:
        raise ValueError("HGSS : inventaire des contenus modifié")
    data = read_json(folder / "content.json")
    if data["sources"] != read_json(CONTRACT) or data["recipe"] != recipe():
        raise ValueError("HGSS : sources ou recette des contenus périmées")
    for name, expected in data["prerequisites"].items():
        if source_digest((prerequisites or folder.parent) / name) != expected:
            raise ValueError(f"HGSS : prérequis de contenu périmé : {name}")
    validate_content(data)
    return data

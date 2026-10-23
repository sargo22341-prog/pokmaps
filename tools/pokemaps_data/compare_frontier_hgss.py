"""Réemploi limité aux données prouvées égales au catalogue versionné de Platine."""

from pathlib import Path

from .frontier_hgss import frontier_catalog
from .pret_gen4_source import read_json
from .rewards_frontier_hgss import reward_catalog
from .sources import DATA_DIR, HGSS_PRET_COMMIT, PRET_COMMITS
from .sources_characters_hgss import source_digest

CONTRACT = Path(__file__).resolve().parents[2] / "docs/generations/combat-hgss-sources.json"
PLATINUM = Path(__file__).resolve().parents[2] / "app/src/main/assets/sinnoh.json"


def battle_catalog(root: Path) -> dict:
    contract = read_json(CONTRACT)
    if contract["hgss_commit"] != HGSS_PRET_COMMIT or contract["platinum_commit"] != PRET_COMMITS["pokeplatinum"]:
        raise ValueError("HGSS : provenance de comparaison Platine incorrecte")
    for name, expected in contract["native"].items():
        if source_digest(root / name) != expected:
            raise ValueError(f"HGSS : source de combat modifiée : {name}")
    if source_digest(PLATINUM) != contract["platinum_catalog_sha256"]:
        raise ValueError("HGSS : catalogue de comparaison Platine modifié")
    native = frontier_catalog(root)
    platinum = read_json(PLATINUM)["groups"]["platinum"]
    if platinum["commit"] != contract["platinum_commit"]:
        raise ValueError("HGSS : commit du catalogue Platine incorrect")
    reference = platinum["battles"]
    common = []
    for key in ("sets", "trainers", "tower_ranges"):
        _equal(native[key], _raw_sets(reference[key]) if key == "sets" else reference[key], key)
        common.append(key)
    for key in ("ranges", "hall"):
        expected = reference["frontier"][key]
        if key == "hall":
            expected = dict(sets=_raw_sets(expected["sets"]), ranks=expected["ranks"])
        _equal(native["frontier"][key], expected, key)
        common.append(f"frontier.{key}")
    differences = _factory_comparison(native["frontier"]["factory"], reference["frontier"]["factory"])
    native["sets"] = reference["sets"]
    native["frontier"]["hall"]["sets"] = reference["frontier"]["hall"]["sets"]
    return dict(
        **native,
        **read_json(DATA_DIR / "hgss_frontier.json"),
        sources=contract,
        rewards=reward_catalog(root),
        comparison=dict(
            common=common,
            factory_differences=differences,
            rule_fr="Configurations et réserves relues dans HGSS. Seules les données égales sont "
            "réutilisées depuis Platine ; les trois entrées différentes des tables de l’Usine restent propres à HGSS.",
        ),
    )


def _raw_sets(rows: list[dict]) -> list[dict]:
    keys = ("id", "species", "moves", "evs", "nature", "item", "form")
    return [{key: row[key] for key in keys} for row in rows]


def _equal(actual: object, expected: object, name: str) -> None:
    if actual != expected:
        raise ValueError(f"HGSS : donnée non commune à Platine, import refusé : {name}")


def _factory_comparison(native: dict, platinum: dict) -> list[dict]:
    differences = []
    for key in ("level50", "open_player", "open_opponent"):
        if len(native[key]) != 10 or len(platinum[key]) != 10:
            raise ValueError(f"HGSS : réserves de l'Usine incomplètes : {key}")
        _equal(native[key][:8], platinum[key][:8], f"factory.{key}.ordinary")
        for index in (8, 9):
            if native[key][index] != platinum[key][index]:
                differences.append(dict(pool=key, index=index, hgss=native[key][index], platinum=platinum[key][index]))
    return differences

"""Invariants hors réseau des réserves de combat et des succès HGSS."""

from .achievement_resources import hgss_achievements
from .compare_frontier_hgss import CONTRACT, PLATINUM, _factory_comparison, _raw_sets
from .pret_gen4_source import read_json


def validate_battles(data: dict) -> None:
    reference = read_json(PLATINUM)["groups"]["platinum"]["battles"]
    if data["sources"] != read_json(CONTRACT):
        raise ValueError("HGSS : contrat de combat périmé")
    for key in ("sets", "trainers", "tower_ranges"):
        if data[key] != reference[key]:
            raise ValueError(f"HGSS : réserve commune de combat modifiée : {key}")
    for key in ("ranges", "hall"):
        if data["frontier"][key] != reference["frontier"][key]:
            raise ValueError(f"HGSS : réserve commune d'installation modifiée : {key}")
    factory = data["frontier"]["factory"]
    differences = _factory_comparison(factory, reference["frontier"]["factory"])
    if differences != data["comparison"]["factory_differences"] or [(r["pool"], r["index"]) for r in differences] != [
        ("level50", 9),
        ("open_player", 8),
        ("open_opponent", 8),
    ]:
        raise ValueError("HGSS : différences de Cardus incorrectes")
    for rows in factory.values():
        for row in rows:
            if not 1 <= row["min"] <= row["max"] <= 950 or not 0 <= row["ivs"] <= 31:
                raise ValueError("HGSS : réserve de location invalide")
    facilities = data["facilities"]
    if [r["id"] for r in facilities] != ["tower", "factory", "hall", "castle", "arcade"]:
        raise ValueError("HGSS : cinq installations attendues")
    for row in facilities:
        expected = (10, 50, 170) if row["id"] == "hall" else (7, 21, 49)
        if (row["series_length"], row["silver"], row["gold"]) != expected or not row["reward_fr"]:
            raise ValueError(f"HGSS : conditions de Photos incorrectes : {row['id']}")
    if len(_raw_sets(data["sets"])) != 950:
        raise ValueError("HGSS : 950 configurations utiles attendues")
    _rewards(data["rewards"])


def _rewards(data: dict) -> None:
    tower = data["tower"]
    if tower["tables"]["ordinary"] != [0, 3, 3, 4, 4, 5, 5, 7] or tower["boss"] != 20:
        raise ValueError("HGSS : Points Combat de la Tour incorrects")
    offers = data["exchange"]["offers"]
    if not 30 <= len(offers) <= 64 or len({r["label"] for r in offers}) != len(offers):
        raise ValueError("HGSS : lots du comptoir incomplets ou dupliqués")
    if any(r["quantity"] != 1 or r["cost"] <= 0 or r["currency"] != "battle_points" for r in offers):
        raise ValueError("HGSS : quantité ou coût de lot incorrect")


def validate_achievements(data: dict) -> None:
    if data != hgss_achievements():
        raise ValueError("HGSS : ensemble partagé de succès incomplet ou modifié")

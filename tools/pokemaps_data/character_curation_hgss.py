"""Libellés français et retouches d'acteurs HGSS avec provenance éditoriale."""

import csv
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"


def editorial_rows(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not 1 <= len(rows) <= 1024 or any(not row.get("source") for row in rows):
        raise ValueError(f"HGSS : provenance éditoriale absente : {name}")
    return rows


def curate_actors(actors: list[dict], trainers: list[dict], offers: list[dict]) -> None:
    classes = {row["constant"]: row["name_fr"] for row in editorial_rows("hgss_trainer_names.csv")}
    if set(classes) != {row["trainer_class"] for row in trainers}:
        raise ValueError("HGSS : noms de classes incomplets ou inutilisés")
    named = {row["sprite"]: row["name_fr"] for row in editorial_rows("hgss_npc_names.csv")}
    named.update(
        {
            row["sprite"]: classes[row["constant"]]
            for row in editorial_rows("hgss_battle_sprites.csv")
            if row["constant"].startswith(("TRAINERCLASS_LEADER_", "TRAINERCLASS_ELITE_FOUR_"))
        }
    )
    by_trainer = {row["id"]: row for row in trainers}
    for trainer in trainers:
        trainer["name_fr"] = classes[trainer["trainer_class"]]
    corrections = {(int(row["header"]), row["identity"]): row for row in editorial_rows("hgss_actor_curation.csv")}
    used = set()
    for actor in actors:
        key = actor["header"], actor["native"]["identity"]
        linked = [o for o in offers if o["bank"] == actor["bank"] and o["instruction"] in actor["service_steps"]]
        actor["name_fr"] = named.get(actor["native"]["sprite"], "Personnage")
        if actor["trainers"]:
            actor["name_fr"] = by_trainer[actor["trainers"][0]]["name_fr"]
        elif linked and actor["name_fr"] == "Personnage":
            actor["name_fr"] = service_name(linked[0]["command"])
        actor["display_offset"] = [0, 0]
        actor["alias_of"] = None
        if key in corrections:
            row = corrections[key]
            used.add(key)
            actor.update(
                name_fr=row["name_fr"] or actor["name_fr"],
                alias_of=row["alias_of"] or None,
                display_offset=[int(row["dx"]), int(row["dy"])],
                curation=row,
            )
            if row["alias_of"]:
                actor["useful"] = False
    if used != set(corrections):
        raise ValueError(f"HGSS : retouches d'acteurs inutilisées : {set(corrections) - used}")


def service_name(command: str) -> str:
    names = {
        "offer_item": "Don d'objet",
        "GiveItem": "Don d'objet",
        "GiveMon": "Pokémon offert",
        "GiveEgg": "Œuf offert",
        "GiveTogepiEgg": "Œuf de Togepi",
        "GiveLoanMon": "Prêt de Pokémon",
        "LoadNPCTrade": "Échange de Pokémon",
        "MartBuy": "Boutique",
        "offer_mart": "Boutique",
        "SpecialMartBuy": "Boutique",
        "offer_special_mart": "Boutique",
        "SealMart": "Marchand de Sceaux",
        "offer_heal": "Soins",
        "HealParty": "Soins",
        "offer_daycare": "Pension",
        "offer_daycare_man": "Pension",
        "PutMonInDaycare": "Pension",
        "RetrieveDaycareMon": "Pension",
        "GiveDaycareEgg": "Œuf de la Pension",
        "offer_tutor": "Maître des capacités",
        "MoveTutorInit": "Maître des capacités",
        "MoveTutorChooseMove": "Maître des capacités",
        "MoveRelearnerInit": "Maître des capacités",
        "MonForgetMove": "Effaceur de capacités",
        "ScrCmd_739": "Fabrication de Balls",
        "GiveOrTakeSeal": "Don de Sceaux",
        "GiveRandomSeal": "Don de Sceaux",
        "GiveRibbon": "Ruban",
        "GiveCoins": "Jetons",
        "GiveAthletePoints": "Points Athlète",
        "GiveApricornFromTree": "Arbre à Noigrumes",
        "ScrCmd_771": "Boutique du Pokéathlon",
        "ScrCmd_772": "Cartes Mémo",
        "ScrCmd_555": "Points Combat",
        "GiveSpikyEarPichu": "Pichu Troizépi",
        "GiveBadge": "Badge",
        "GivePokedex": "Pokédex",
        "GiveRunningShoes": "Chaussures de Sport",
        "RegisterGearNumber": "Numéro de Pokématos",
    }
    if command not in names:
        raise ValueError(f"HGSS : service sans libellé français : {command}")
    return names[command]

"""Consultation des dons et services de scène, sans attribution fictive à un PNJ."""

from collections import defaultdict

from .guide_resources_hgss import Article
from .maps_layout import identifier
from .placement_hgss import read_placement_json
from .sources import PREVIEW_DIR


def scene_articles(content: dict) -> list[Article]:
    characters = read_placement_json(PREVIEW_DIR / "hgss-characters/characters.json")
    maps = read_placement_json(PREVIEW_DIR / "hgss-maps/atlas/catalog.json")
    lookup = {r["header"]: r for r in maps["maps"]}
    banks: dict[int, set[int]] = defaultdict(set)
    for actor in characters["actors"] + characters["scenes"]:
        banks[actor["bank"]].add(actor["header"])
    grouped: dict[int, list[dict]] = defaultdict(list)
    for step in characters["service_steps"]:
        if not step["actors"]:
            grouped[step["bank"]].append(step)
    result = []
    for bank, steps in sorted(grouped.items()):
        places = [lookup[h] for h in sorted(banks[bank]) if h in lookup]
        if not places:
            raise ValueError(f"HGSS : service de scène sans lieu : banque {bank}")
        lines = []
        for step in steps:
            text = _description(step, content)
            costs = [_cost(c, content["item_names_fr"]) for c in step["costs"]]
            if costs:
                text += " Coût : " + " et ".join(costs) + "."
            if step["version"] in (7, 8):
                text += " " + {7: "Or HeartGold uniquement.", 8: "Argent SoulSilver uniquement."}[step["version"]]
            if step["conditions_fr"]:
                text += " Conditions : " + " ; ".join(step["conditions_fr"]) + "."
            lines.append(text)
        links = ", ".join(f"[[place:{identifier(p['const'])}|{p['name_fr']}]]" for p in places)
        intro = "Dons et services de scène : leurs conditions ne sont pas nécessairement réunies à la même étape."
        text = intro + "\n\n" + "\n\n".join(dict.fromkeys(lines)) + "\n\nLieux : " + links
        result.append(
            Article(
                f"hgss-scene-{bank}",
                "Objets et services — " + places[0]["name_fr"],
                text,
                sources=(characters["scripts"][str(bank)]["source"],),
            )
        )
    return result


def _cost(cost: dict, items: dict[str, str]) -> str:
    if cost["currency"] == "item":
        return f"{items[str(cost['item'])]} × {cost['amount']}"
    labels = {"money": "₽", "coins": "jetons", "battle_points": "Points Combat", "athlete_points": "Points Athlète"}
    return f"{cost['amount']} {labels[cost['currency']]}"


def _description(step: dict, content: dict) -> str:
    command, values = step["command"], step["values"]
    if step.get("kind") == "apricorn_return":
        return "Fargas : une Ball par Noigrume déposé, remise le jour suivant."
    if command in {"GiveItem", "offer_item"}:
        return f"{content['item_names_fr'][str(values[0])]} × {values[1]}."
    if command == "GiveMon":
        number = values[0]
        return f"[[pokemon:{number}|{content['names_fr'][str(number)]}]], niveau {values[1]}."
    labels = {
        "HealParty": "Soins de l'équipe.",
        "RegisterGearNumber": "Numéro ajouté au Pokématos.",
        "GiveBadge": "Badge remis après l'épreuve.",
        "ScrCmd_771": "Comptoir des prix quotidiens du Pokéathlon.",
        "ScrCmd_772": "Comptoir des Cartes Mémo, selon celles déjà reçues.",
        "GivePokedex": "Pokédex reçu.",
        "GiveRunningShoes": "Chaussures de Sport reçues.",
    }
    if command not in labels:
        raise ValueError(f"HGSS : service de scène sans texte français : {command}")
    return labels[command]

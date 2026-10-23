"""Invariants des guides, objectifs et activités HGSS, sans accès au réseau."""

from .guides_hgss import map_entries, validate_guides
from .sources import HGSS_PRET_COMMIT
from .validate_combat_hgss import validate_achievements, validate_battles


def validate_content(data: dict) -> None:
    if data["schema"] != 1 or data["commit"] != HGSS_PRET_COMMIT or data["status"] != "preparatory":
        raise ValueError("HGSS : schéma ou provenance des contenus incorrects")
    if data["versions"] != ["heartgold", "soulsilver"]:
        raise ValueError("HGSS : versions de contenu incorrectes")
    validate_guides(data["guides"])
    headers = {row["header"] for row in map_entries()}
    for guide in data["guides"]:
        if any(p["header"] not in headers for p in guide["places"]):
            raise ValueError(f"HGSS : lieu de guide inconnu : {guide['id']}")
        if any(a["header"] not in {p["header"] for p in guide["places"]} for a in guide["actors"]):
            raise ValueError(f"HGSS : acteur hors des lieux du guide : {guide['id']}")
        for item in guide["items"]:
            _guide_item(item, data["item_names_fr"])
    _objectives(data["objectives"])
    _activities(data["activities"])
    validate_battles(data["battles"])
    validate_achievements(data["achievements"])
    entries = data["calendar"]["entries"]
    if len({r["contact"] for r in entries}) != len(entries) or sum(r["leader"] for r in entries) != 16:
        raise ValueError("HGSS : calendrier des seize Champions incomplet")
    for row in data["weekly"]:
        if not row["sources"] or not row["weekdays"] or any(day not in range(7) for day in row["weekdays"]):
            raise ValueError(f"HGSS : rendez-vous hebdomadaire invalide : {row['id']}")


def _guide_item(row: dict, names: dict[str, str]) -> None:
    values = row["values"]
    if len(values) == 2 and str(values[0]) in names and type(values[1]) is int and 1 <= values[1] <= 999:
        return
    rule = row["quantity_rule"]
    if not values and rule and rule["kind"] == "matching_deposit" and rule["output_per_input"] == 1:
        return
    raise ValueError(f"HGSS : objet de guide non résolu : {row['id']}")


def _objectives(rows: list[dict]) -> None:
    if len(rows) != 54 or len({r["id"] for r in rows}) != 54:
        raise ValueError("HGSS : cinquante-quatre configurations d'objectifs attendues")
    for row in rows:
        if row["version"] not in ("heartgold", "soulsilver"):
            raise ValueError(f"HGSS : version d'objectif inconnue : {row['id']}")
        if any(row[key] != sorted(set(row[key])) for key in ("national", "regional", "excluded")):
            raise ValueError(f"HGSS : objectif non trié ou dupliqué : {row['id']}")
        national, regional, excluded = (set(row[key]) for key in ("national", "regional", "excluded"))
        if national & excluded or national | excluded != set(range(1, 494)) or not regional <= national:
            raise ValueError(f"HGSS : partition d'objectif invalide : {row['id']}")
        if not set(row["starters"].values()) <= national:
            raise ValueError(f"HGSS : starter choisi absent : {row['id']}")
        if {r["species"] for r in row["exclusions"]} != excluded or any(not r["reason_fr"] for r in row["exclusions"]):
            raise ValueError(f"HGSS : exclusions non justifiées : {row['id']}")
        forbidden = {384, 483, 484, 487, 492, 493}
        forbidden |= {381, 383, 140, 345, 408, 410} if row["version"] == "heartgold" else {380, 382, 138, 347, 408, 410}
        if forbidden & national:
            raise ValueError(f"HGSS : provenance externe comptée comme locale : {row['id']}")


def _activities(data: dict) -> None:
    expected = {
        "pokeathlon",
        "noigrumes",
        "noigrume-drink",
        "safari",
        "pokewalker",
        "frontier",
        "contest",
        "radio",
        "pokegear",
        "photos",
        "voltorb",
        "berries",
        "external",
    }
    guides = data["guides"]
    if {row["id"] for row in guides} != expected or len(guides) != len(expected):
        raise ValueError("HGSS : activités manquantes ou dupliquées")
    if any(not row["text_fr"].strip() or not row["sources"] for row in guides):
        raise ValueError("HGSS : activité sans explication ou provenance")
    if len(data["safari"]) != 12 or len(data["apricorns"]["conversions"]) != 7:
        raise ValueError("HGSS : Safari ou Noigrumes incomplets")
    if len(data["aprijuice"]["contributions"]) != 7:
        raise ValueError("HGSS : Noigrumes à boire incomplets")
    if len(data["pokeathlon"]["shops"]["daily"]) != 14 or len(data["contest"]) != 6:
        raise ValueError("HGSS : calendriers d'activités incomplets")
    courses = data["pokewalker"]["courses"]
    if [row["index"] for row in courses] != list(range(27)):
        raise ValueError("HGSS : parcours Pokéwalker incomplets")
    for row in courses:
        if row["ordinary_objective"] or len(row["pokemon"]) != 6 or len(row["items"]) != 10:
            raise ValueError(f"HGSS : parcours Pokéwalker invalide : {row['index']}")
    if len(data["voltorb_flip"]["configurations"]) != 80 or not data["photos"]["sites"]:
        raise ValueError("HGSS : Voltorbataille ou photos incomplets")

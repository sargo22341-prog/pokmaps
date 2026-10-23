"""Invariants des équipes, liens, offres, calendriers et aperçus HGSS."""

from .sources import HGSS_PRET_COMMIT


def validate_character_catalog(data: dict) -> None:
    if (data["schema"], data["commit"], data["status"]) != (2, HGSS_PRET_COMMIT, "resolved"):
        raise ValueError("HGSS : contrat des personnages incorrect")
    if data["versions"] != ["heartgold", "soulsilver"]:
        raise ValueError("HGSS : versions des personnages incorrectes")
    known = {row["id"] for row in data["trainers"]}
    if len(data["trainers"]) != 737 or known != set(range(1, 738)):
        raise ValueError("HGSS : équipes absentes ou répétées")
    for battle in data["battles"]:
        bank = data["scripts"][str(battle["bank"])]
        instruction = bank["instructions"][battle["instruction"]]
        if battle["line"] != instruction["line"] or battle["command"] != instruction["command"]:
            raise ValueError(f"HGSS : combat sans instruction correspondante : {battle['source']}:{battle['line']}")
        if set(battle["trainers"]) - known or battle["partner"] in battle["opponents"]:
            raise ValueError("HGSS : adversaire ou partenaire de combat incorrect")
    _validate_actors(data, known)
    for item in data["field_items"]:
        value = item["item"]
        if value["kind"] != "visible_variable" and not (1 <= value["item"] <= 535 and 1 <= value["quantity"] <= 999):
            raise ValueError(f"HGSS : objet placé invalide : {item['source']}:{item['event']}")
    if len(data["rematches"]["series"]) != 63:
        raise ValueError("HGSS : séries de revanches incomplètes")
    for row in data["rematches"]["series"]:
        if len(row["teams"]) != 6 or set(row["teams"]) - known - {0, 65535}:
            raise ValueError("HGSS : équipe de revanche inconnue")
    _validate_resolved(data, known)


def _validate_resolved(data: dict, known: set[int]) -> None:
    if len(data["resolved_battles"]) != 123 or len(data["calendar"]["entries"]) != 63:
        raise ValueError("HGSS : combats ou calendrier incomplets")
    actors = {(a["header"], a["event"]): a for a in data["actors"]}
    for battle in data["resolved_battles"]:
        teams = {t for v in battle["variants"] for t in v["opponents"]}
        teams |= {v["partner"] for v in battle["variants"] if v["partner"]}
        if teams - known or teams != {a["trainer"] for a in battle["actors"]}:
            raise ValueError("HGSS : attribution de combat incomplète")
        if any((a["header"], a["event"]) not in actors for a in battle["actors"]):
            raise ValueError("HGSS : acteur de combat absent")
    for offer in data["service_steps"]:
        if any(value in ("inconnue", "externe") for value in (*offer["values"], *offer["payments"])):
            raise ValueError("HGSS : offre non résolue")
        if any(not isinstance(cost["amount"], int) or cost["amount"] <= 0 for cost in offer["costs"]):
            raise ValueError("HGSS : coût d'offre invalide")
    useful = [a for a in actors.values() if a["useful"]]
    sprites = {s["sprite"] for s in data["sprites"] if s["status"] == "decoded"}
    if any(a["native"]["sprite"] not in sprites or not a["placement"]["inside"] for a in useful):
        raise ValueError("HGSS : aperçu ou placement de personnage absent")
    if data["placements"]["count"] != len(useful):
        raise ValueError("HGSS : couverture des placements incomplète")
    if sum(e["leader"] for e in data["calendar"]["entries"]) != 16 or len(data["calendar"]["league"]) != 5:
        raise ValueError("HGSS : champions ou Ligue incomplets")


def _validate_actors(data: dict, known: set[int]) -> None:
    keys = [(row["header"], row["event"]) for row in data["actors"]]
    if len(keys) != len(set(keys)):
        raise ValueError("HGSS : acteur répété dans un lieu")
    for actor in data["actors"]:
        if set(actor["trainers"]) - known:
            raise ValueError(f"HGSS : acteur sans équipe : {actor['native']['identity']}")
        bank = data["scripts"][str(actor["bank"])]
        if actor["script_entry"] and actor["script_entry"] not in bank["labels"]:
            raise ValueError(f"HGSS : acteur sans entrée de script : {actor['native']['identity']}")
        for index in actor["battles"]:
            if not any(b["bank"] == actor["bank"] and b["instruction"] == index for b in data["battles"]):
                raise ValueError(f"HGSS : acteur lié à un combat absent : {actor['native']['identity']}")

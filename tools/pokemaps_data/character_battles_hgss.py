"""Attribution des combats de scénario HGSS aux acteurs réellement présents."""

from .character_curation_hgss import editorial_rows
from .pret_hgss_scripts import Script


def bind_battles(
    actors: list[dict], battles: list[dict], trainers: list[dict], scripts: dict[int, Script]
) -> list[dict]:
    portraits = {r["constant"]: r["sprite"] for r in editorial_rows("hgss_battle_sprites.csv")}
    teams = {row["id"]: row for row in trainers}
    curated = {(int(r["bank"]), int(r["trainer"])): r for r in editorial_rows("hgss_battle_actors.csv")}
    used = set()
    missing = []
    for battle in battles:
        battle["actors"] = []
        ids = {trainer for variant in battle["variants"] for trainer in variant["opponents"]}
        ids |= {variant["partner"] for variant in battle["variants"] if variant["partner"]}
        for trainer in sorted(ids):
            direct = [a for a in actors if a["bank"] == battle["bank"] and battle["instruction"] in a["battles"]]
            sprite = portraits.get(teams[trainer]["trainer_class"])
            matched = [a for a in actors if a["bank"] == battle["bank"] and a["native"]["sprite"] == sprite]
            candidates = [a for a in direct if sprite is None or a["native"]["sprite"] == sprite] or matched
            key = battle["bank"], trainer
            if key in curated:
                candidates = [
                    a for a in actors if a["bank"] == key[0] and a["native"]["identity"] == curated[key]["identity"]
                ]
                used.add(key)
            if len(candidates) > 1:
                referenced = {
                    arg
                    for step in scripts[battle["bank"]].steps[: battle["instruction"]]
                    for arg in step.arguments
                    if arg.startswith("obj_") and arg != "obj_player"
                }
                candidates = [a for a in candidates if a["native"]["identity"] in referenced]
            if len(candidates) != 1:
                missing.append(
                    dict(
                        bank=battle["bank"],
                        instruction=battle["instruction"],
                        trainer=trainer,
                        constant=teams[trainer]["constant"],
                        candidates=[a["native"]["identity"] for a in candidates],
                    )
                )
                continue
            actor = candidates[0]
            actor["useful"] = True
            actor["trainers"] = sorted(set(actor["trainers"]) | {trainer})
            battle["actors"].append(dict(header=actor["header"], event=actor["event"], trainer=trainer))
    if used != set(curated):
        raise ValueError("HGSS : attributions de combat inutilisées")
    return missing

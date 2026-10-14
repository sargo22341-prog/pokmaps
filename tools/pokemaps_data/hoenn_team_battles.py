"""Combats scénarisés reliés aux acteurs, y compris les combats sans script d'interaction."""

from dataclasses import replace

from .pret_gen3_maps import Gen3Event, Gen3Map
from .pret_gen3_offers import Gen3Offers, ScriptOffers
from .pret_gen3_trainers import Gen3Trainer


def team_battle(
    current: Gen3Map,
    index: int,
    event: Gen3Event,
    result: ScriptOffers,
    reader: Gen3Offers,
    trainers: dict[str, Gen3Trainer],
) -> ScriptOffers:
    result = _actor_battles(event, result, trainers)
    result = _weather_offers(current, index, result)
    slots = {
        "PetalburgWoods": {3: 0},
        "SlateportCity_OceanicMuseum_2F": {3: 0, 4: 1},
        "SeafloorCavern_Room9": {2: 0},
    }
    if current.label == "MossdeepCity_SpaceCenter_2F":
        names = {
            5: "TRAINER_GRUNT_SPACE_CENTER_6",
            6: "TRAINER_GRUNT_SPACE_CENTER_5",
            7: "TRAINER_GRUNT_SPACE_CENTER_7",
            8: "TRAINER_TABITHA_MOSSDEEP",
            9: "TRAINER_MAXIE_MOSSDEEP",
        }
        trainer = names.get(index)
        return replace(result, trainers=(trainer,)) if trainer in trainers else result
    slot = slots.get(current.label, {}).get(index)
    if slot is None:
        return result
    candidates = []
    for label, block in reader.scripts.blocks.items():
        if not label.startswith(current.label + "_"):
            continue
        for instruction in block.lines:
            if not instruction.command.startswith("trainerbattle"):
                continue
            name = instruction.args[1] if instruction.command == "trainerbattle" else instruction.args[0]
            trainer = trainers.get(name)
            if trainer and any(team in trainer.trainer_class for team in ("AQUA", "MAGMA")) and name not in candidates:
                candidates.append(name)
    expected = 2 if current.label == "SlateportCity_OceanicMuseum_2F" else 1
    if len(candidates) != expected:
        raise ValueError(f"{current.label} : {len(candidates)} combats d'équipe, {expected} attendus")
    return replace(result, trainers=(candidates[slot],))


def _actor_battles(event: Gen3Event, result: ScriptOffers, trainers: dict[str, Gen3Trainer]) -> ScriptOffers:
    sprite = str(event.value("graphics_id"))
    retained = []
    for name in result.trainers:
        team = next((team for team in ("AQUA", "MAGMA") if team in trainers[name].trainer_class), None)
        if team and sprite.startswith("OBJ_EVENT_GFX_VAR_"):
            raise ValueError(f"{name} : apparence variable du combattant non résolue : {sprite}")
        if (
            team is None
            or team in sprite
            or (team, sprite) in {("AQUA", "OBJ_EVENT_GFX_ARCHIE"), ("MAGMA", "OBJ_EVENT_GFX_MAXIE")}
        ):
            retained.append(name)
    # Le capitaine Poupe et Pierre déclenchent une scène, mais ne sont pas les ennemis qu'elle fait combattre.
    return replace(result, trainers=tuple(retained))


def _weather_offers(current: Gen3Map, index: int, result: ScriptOffers) -> ScriptOffers:
    if current.label != "Route119_WeatherInstitute_2F":
        return result
    # Le scientifique donne Morphéo après le départ de l'admin ; le surnom appartient à ce don unique.
    offers = tuple(
        offer
        for offer in result.offers
        if offer.kind != "rename_pokemon" and not (index == 3 and offer.pokemon == "SPECIES_CASTFORM")
    )
    return replace(result, offers=offers)

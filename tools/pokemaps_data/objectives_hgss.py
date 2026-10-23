"""Objectifs déterministes par cartouche et par choix de starters HGSS."""

from itertools import product

from .pokeapi import PokeApi
from .special_wild_hgss import SafariConfiguration, safari_slots


def _wild_species(encounters: dict, version: str) -> set[int]:
    headers = {row["header"] for row in encounters["maps"]}
    banks = {row["bank"] for row in encounters["banks"] if set(row["headers"]) & headers}
    result = {
        slot["species"]
        for table in encounters["distributions"] + encounters["headbutt"]
        if table["version"] == version
        and table["bank"] in (headers if table["method"].startswith("headbutt-") else banks)
        for slot in table["slots"]
    }
    special = encounters["special_wild"]
    result.update(slot["species"] for row in special["contest"] for slot in row["slots"])
    for area in special["safari"]:
        for method in ("land", "surf", "oldrod", "goodrod", "superrod"):
            table = area[method]
            for period in ("morn", "day", "nite"):
                result.update(_safari_species(table, period, special["species_ids"]))
    return result


def _safari_species(table: dict, period: str, species: dict[str, int]) -> set[int]:
    result = {slot.species for slot in safari_slots(table, period, SafariConfiguration(), species)}
    kinds = ("PLAINS", "FOREST", "PEAK", "WATER")
    # Les facteurs changent uniquement aux dizaines. Le minimum de blocs rend aussi
    # minimales les conditions concurrentes : augmenter un compte ne peut libérer un emplacement.
    for days in range(0, 251, 10):
        factors = SafariConfiguration(days, (1, 1, 1, 1), national=True, objects_unlocked=True).points
        for bonus in table["bonus_mons"]:
            blocks = [0, 0, 0, 0]
            for condition in bonus["conditions"]:
                index = kinds.index(condition["object_type"].removeprefix("SAFARI_ZONE_OBJECT_TYPE_"))
                needed = (condition["count"] + factors[index] - 1) // factors[index]
                blocks[index] = max(blocks[index], needed)
            if sum(blocks) > 30:
                continue
            config = SafariConfiguration(days, tuple(blocks), national=True, objects_unlocked=True)
            result.update(slot.species for slot in safari_slots(table, period, config, species))
    return result


def _local_scripts(encounters: dict, version: str) -> set[int]:
    rows = encounters["obtainings"]["scripts"]
    result = {n for row in rows if row["ordinary_objective"] for n in row["species"]}
    # Les scripts de réanimation acceptent aussi les fossiles importés ; leurs tables ne prouvent pas l'accès.
    excluded = {140, 345, 408, 410, 381, 383} if version == "heartgold" else {138, 347, 408, 410, 380, 382}
    result.difference_update(excluded)
    result.difference_update({1, 4, 7, 152, 155, 158, 252, 255, 258})
    result.update((21, 213))
    return result


def close_collection(initial: set[int], evolutions: list[dict], breeds: dict[int, int], trades: list[dict]) -> set[int]:
    result = set(initial)
    for _ in range(493):
        additions = {e["target"] for e in evolutions if e["access"] == "local" and e["species"] in result}
        additions.update(t["given"] for t in trades if t["requested"] in result and not t["loan"])
        if 132 in result:
            additions.update(baby for parent, baby in breeds.items() if parent in result)
        if additions <= result:
            return result
        result.update(additions)
    raise ValueError("HGSS : fermeture des objectifs non convergente après 493 passages")


def objective_catalog(
    encounters: dict, pokemon: dict, species_ids: dict[str, int], breeds: dict[int, int], trades: list[dict]
) -> list[dict]:
    evolutions = [
        row | dict(species=species_ids[row["species"]], target=species_ids[row["target"]])
        for row in pokemon["evolutions"]
    ]
    regional = {row["id"] for row in pokemon["pokemon"] if row["regional"]}
    result = []
    for version in ("heartgold", "soulsilver"):
        base = _wild_species(encounters, version) | _local_scripts(encounters, version)
        for johto, kanto, hoenn in product((152, 155, 158), (1, 4, 7), (252, 255, 258)):
            captured = close_collection(base | {johto, kanto, hoenn}, evolutions, breeds, trades)
            result.append(
                dict(
                    id=f"{version}-{johto}-{kanto}-{hoenn}",
                    version=version,
                    starters=dict(johto=johto, kanto=kanto, hoenn=hoenn),
                    national=sorted(captured),
                    regional=sorted(captured & regional),
                    excluded=sorted(set(range(1, 494)) - captured),
                    exclusions=[
                        dict(species=n, reason_fr=_exclusion(n, evolutions))
                        for n in sorted(set(range(1, 494)) - captured)
                    ],
                )
            )
    return result


def _exclusion(species: int, evolutions: list[dict]) -> str:
    if species in set(range(1, 10)) | set(range(152, 161)) | set(range(252, 261)):
        return "Autre choix de starter, incompatible sur cette sauvegarde."
    if species in {138, 139, 140, 141, 345, 346, 347, 348, 408, 409, 410, 411}:
        return "Fossile non obtenu dans cette cartouche ; import nécessaire."
    if species in {380, 381}:
        return "Autre errant : Mystécristal externe ou échange nécessaire."
    if species in {382, 383, 384}:
        return "Autre cartouche HGSS nécessaire pour cette légende."
    external = [e["condition_fr"] for e in evolutions if e["target"] == species and e["access"] != "local"]
    if external:
        return " ".join(external)
    return "Aucune provenance locale dans cette cartouche ; échange, transfert, accessoire ou événement externe requis."


def breeding_roots(api: PokeApi) -> dict[int, int]:
    rows = {int(row["id"]): row for row in api.table("pokemon_species") if int(row["id"]) <= 493}
    result = {}
    for number in rows:
        parent = number
        for _ in range(4):
            previous = rows[parent]["evolves_from_species_id"]
            if not previous:
                break
            parent = int(previous)
        else:
            raise ValueError(f"HGSS : chaîne de reproduction trop profonde : {number}")
        if parent != number:
            result[number] = parent
    # Les deux espèces peuvent naître d'une même lignée, même sans lien d'évolution PokéAPI.
    result.update({29: 32, 32: 29, 313: 314, 314: 313})
    return result

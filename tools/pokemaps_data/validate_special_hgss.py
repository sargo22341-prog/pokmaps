"""Validation des catalogues préparatoires des lots HGSS 4C et 4D."""

from .encounters_hgss import Slot
from .special_wild_hgss import SafariConfiguration, safari_slots


def validate_special_wild(catalog: dict) -> None:
    contest = catalog["contest"]
    if {(r["weekday"], r["national"]) for r in contest} != {(d, n) for d in (1, 3, 5) for n in (False, True)}:
        raise ValueError("HGSS : configurations du concours incomplètes")
    if len(contest) != 6:
        raise ValueError("HGSS : six configurations du concours attendues")
    for row in contest:
        slots = tuple(Slot(**s) for s in row["slots"])
        if len(slots) != 10 or sum(s.chance for s in slots) != 100:
            raise ValueError("HGSS : distribution du concours invalide")
    areas = catalog["safari"]
    if len(areas) != 12 or len({a["area"] for a in areas}) != 12:
        raise ValueError("HGSS : habitats Safari incomplets")
    for area in areas:
        for method in ("land", "surf", "oldrod", "goodrod", "superrod"):
            table = area[method]
            for period in ("morn", "day", "nite"):
                safari_slots(table, period, SafariConfiguration(), catalog["species_ids"])
                for mon in table["mons"][period] + [b[period] for b in table["bonus_mons"]]:
                    Slot(catalog["species_ids"][mon["species"]], mon["level"], mon["level"], 10)


def validate_obtainings(catalog: dict) -> None:
    records = catalog["scripts"]
    if not 1 <= len(records) <= 1000 or len({r["id"] for r in records}) != len(records):
        raise ValueError("HGSS : inventaire des obtentions vide, dupliqué ou trop volumineux")
    for row in records:
        if not row["source"].startswith("files/fielddata/script/scr_seq/") or row["line"] < 1:
            raise ValueError("HGSS : provenance d'obtention invalide")
        if any(type(n) is not int or not 1 <= n <= 493 for n in row["species"]):
            raise ValueError("HGSS : espèce d'obtention invalide")
        if row["access"] not in ("external_event", "external_transfer", "local_conditional"):
            raise ValueError("HGSS : accès d'obtention inconnu")
        external = row["access"] != "local_conditional"
        if row["ordinary_objective"] != (not external) or external != bool(row["exclusion_fr"]):
            raise ValueError("HGSS : exclusion des objectifs ordinaires incohérente")
    for key, access in (
        ("pokewalker", "accessory"),
        ("distributions", "external_event"),
        ("transfers", "external_transfer"),
    ):
        row = catalog[key]
        if row["access"] != access or row["ordinary_objective"] is not False or not row["exclusion_fr"]:
            raise ValueError(f"HGSS : exclusion externe manquante : {key}")
    if catalog["pokewalker"]["map_headers"]:
        raise ValueError("HGSS : le Pokéwalker ne doit pas être placé sur la carte")
    trades = catalog["trades"]
    if len(trades) != 13 or {r["index"] for r in trades} != set(range(13)):
        raise ValueError("HGSS : échanges incomplets")
    for row in trades:
        if not 1 <= row["given"] <= 493 or not 0 <= row["requested"] <= 493:
            raise ValueError("HGSS : échange invalide")

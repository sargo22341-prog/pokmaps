"""Calendrier du Pokématos, déblocages des revanches et variantes de la Ligue HGSS."""

import re
from dataclasses import asdict
from pathlib import Path

from .conditions_hgss import translate_conditions
from .pret_gen4_flow_chains import Chains
from .pret_gen4_source import read_text
from .pret_hgss_flow import HgssFlow


def phone_headers(root: Path) -> list[list[dict]]:
    source = "src/application/pokegear/phone/phone_generic_headers.c"
    body = read_text(root / source).split("sGenericPhoneCallHeaders[] = {", 1)[1].split("\n};", 1)[0]
    body = re.sub(r"//[^\n]*", "", body)
    rows = []
    for token, fields in re.findall(r"(PHONE_GENERIC_(?:TERM|NULL))|\{([^{}]+)\}", body):
        if token:
            rows.append(dict(type="PHONECALLGENERIC_NIL" if token.endswith("TERM") else "PHONECALLGENERIC_NONE"))
        else:
            values = dict(re.findall(r"\.(\w+)\s*=\s*(\w+)", fields))
            if set(values) != {"type", "chance", "scriptType", "scriptID"}:
                raise ValueError("HGSS : en-tête téléphonique illisible")
            rows.append(values | dict(chance=int(values["chance"]), source=source))
    if len(rows) != 75 * 16:
        raise ValueError(f"HGSS : 1 200 en-têtes téléphoniques attendus : {len(rows)}")
    definitions = read_text(root / "src/application/pokegear/phone/phone_script_defs.c")
    kinds = {
        name: kind
        for name, kind in re.findall(r"// (PHONE_SCRIPT_\d+)\s*\{.*?\.scriptType\s*=\s*(\w+)", definitions, re.S)
    }
    for row in rows:
        if "scriptID" in row:
            if row["scriptID"] != "PHONE_SCRIPT_NONE" and row["scriptID"] not in kinds:
                raise ValueError(f"HGSS : script téléphonique inconnu : {row['scriptID']}")
            row["rematch"] = kinds.get(row["scriptID"], "PHONESCRIPTTYPE_NONE") == "PHONESCRIPTTYPE_REMATCH"
            row["conditions_fr"] = generic_condition(row["type"])
    return [rows[i : i + 16] for i in range(0, len(rows), 16)]


def generic_condition(kind: str) -> list[str]:
    rules = {
        "PHONECALLGENERIC_FIGHTPOSTROCKETS": [
            "Aucun rendez-vous ni cadeau en attente",
            "Tour Radio libérée pour une revanche",
        ],
        "PHONECALLGENERIC_POSTROCKETWEEKTIME": ["Tour Radio libérée", "Jour et période du contact"],
        "PHONECALLGENERIC_FIGHTPOSTROCKETSNOTBUGCONTEST": [
            "Tour Radio libérée",
            "Revanche en attente",
            "Au Parc Naturel, hors Concours de capture d'insectes",
        ],
        "PHONECALLGENERIC_GIFTNOTBUGCONTEST": [
            "Cadeau en attente",
            "Au Parc Naturel, hors Concours de capture d'insectes",
        ],
        "PHONECALLGENERIC_BUGCONTESTDAYS": ["Mardi, jeudi ou samedi"],
        "PHONECALLGENERIC_DURINGROCKETS": ["Occupation de la Tour Radio par la Team Rocket"],
        "PHONECALLGENERIC_RAND1": [],
        "PHONECALLGENERIC_RAND6": [],
        "PHONECALLGENERIC_NIL": [],
        "PHONECALLGENERIC_NONE": [],
    }
    if kind not in rules:
        raise ValueError(f"HGSS : condition d'appel inconnue : {kind}")
    return rules[kind]


def calendar_catalog(
    root: Path, rematches: dict, flows: dict[int, HgssFlow], trainers: list[dict], actors: list[dict]
) -> dict:
    headers = phone_headers(root)
    by_trainer = {row["id"]: row for row in trainers}
    series = {row["base"]: row for row in rematches["series"]}
    entries = []
    for contact in rematches["contacts"]:
        if not contact["rematch"]:
            continue
        registered = _registration_sites(contact, flows, actors)
        day = contact["rematchWeekday"].removeprefix("RTC_WEEK_")
        period = contact["rematchTimeOfDay"].removeprefix("TIMEOFDAY_WILD_")
        leader = contact["trainerClass"].startswith("TRAINERCLASS_LEADER_")
        _registration_presence(registered, actors, by_trainer[contact["trainer"]]["name_fr"] if leader else None)
        entries.append(
            dict(
                contact=contact["id"],
                name_fr=by_trainer[contact["trainer"]]["name_fr"],
                leader=leader,
                weekday=day,
                period=period,
                weekday_fr=weekday_label(day),
                period_fr=period_label(period),
                base=contact["trainer"],
                teams=series[contact["trainer"]]["teams"],
                registration=registered,
                destination="MAP_SAFFRON_FIGHTING_DOJO" if leader else contact["mapId"],
                outgoing=headers[contact["index"]][:8],
                incoming=headers[contact["index"]][8:],
                conditions_fr=(
                    [
                        "Seize Badges",
                        "Numéro enregistré",
                        "Appeler hors du lieu du contact",
                        "Aucun rendez-vous déjà actif",
                        "Accepter le rendez-vous",
                    ]
                    if leader
                    else ["Numéro enregistré", "Respecter les conditions de l'appel retenu"]
                ),
                daytime_only=contact["index"] == 16,
            )
        )
    return dict(
        entries=entries,
        unlocks=_unlocks(flows),
        league=_league(flows),
        selection_source="src/overlay_26_022598C0.c",
        time_source="src/gf_rtc.c",
        chance_fr="Les tests de chance restent ordonnés et conditionnels ; ils ne prédisent aucun appel.",
    )


def _registration_sites(contact: dict, flows: dict[int, HgssFlow], actors: list[dict]) -> list[dict]:
    sites = []
    for bank, adapted in flows.items():
        for step in adapted.flow.steps.values():
            if step.command != "RegisterGearNumber":
                continue
            if step.arguments != (contact["index"],):
                continue
            conditions = [asdict(c) for c in Chains(adapted.flow).conditions(step.key)]
            sites.append(
                dict(
                    bank=bank,
                    instruction=adapted.original[int(step.key)],
                    source=adapted.flow.name,
                    conditions=conditions,
                    conditions_fr=translate_conditions(conditions),
                    actors=[
                        dict(header=a["header"], event=a["event"])
                        for a in actors
                        if a["bank"] == bank and adapted.original[int(step.key)] in a["service_steps"]
                    ],
                )
            )
    if not sites:
        sites = [
            dict(
                kind="standard_trainer",
                base=contact["trainer"],
                conditions_fr=["Dresseur vaincu", "Accepter son numéro de Pokématos"],
                actors=[
                    dict(header=a["header"], event=a["event"]) for a in actors if contact["trainer"] in a["trainers"]
                ],
            )
        ]
    return sites


def _registration_presence(sites: list[dict], actors: list[dict], name: str | None) -> None:
    lookup = {(a["header"], a["event"]): a for a in actors}
    for site in sites:
        candidates = [lookup[a["header"], a["event"]] for a in site["actors"]]
        named = [a for a in candidates if a["name_fr"] == name] if name else []
        if named:
            candidates = named
        site["actors"] = [dict(header=a["header"], event=a["event"], presence=a["presence"]) for a in candidates]


def _unlocks(flows: dict[int, HgssFlow]) -> list[dict]:
    result = []
    for group, flag, label in (
        (2, 0x97D, "Tour Radio libérée"),
        (3, 0x97E, "Entrée au Panthéon"),
        (4, 0x97F, "Blue vaincu"),
    ):
        sites = [
            dict(bank=bank, source=adapted.flow.name, step=step.source)
            for bank, adapted in flows.items()
            for step in adapted.flow.steps.values()
            if step.command == "set_flag" and step.arguments == (flag,)
        ]
        if len(sites) != 1:
            raise ValueError(f"HGSS : déblocage de revanche non unique : {flag:#x}")
        result.append(dict(group=group, flag=flag, condition_fr=label, sites=sites))
    return result


def _league(flows: dict[int, HgssFlow]) -> list[dict]:
    rows = []
    for bank in range(820, 825):
        adapted = flows[bank]
        teams = [s.arguments[0] for s in adapted.flow.steps.values() if s.command == "TrainerBattle"]
        if len(teams) != 2 or not any(
            s.command == "compare_value" and s.arguments == (0x4135, 8) for s in adapted.flow.steps.values()
        ):
            raise ValueError(f"HGSS : variantes de Ligue non reconnues : {bank}")
        rows.append(
            dict(
                bank=bank,
                initial=teams[1],
                rematch=teams[0],
                variable=0x4135,
                threshold=8,
                condition_fr="Huit Badges de Kanto pour l'équipe renforcée",
                source=adapted.flow.name,
            )
        )
    return rows


def weekday_label(day: str) -> str:
    return {
        "SUNDAY": "Dimanche",
        "MONDAY": "Lundi",
        "TUESDAY": "Mardi",
        "WEDNESDAY": "Mercredi",
        "THURSDAY": "Jeudi",
        "FRIDAY": "Vendredi",
        "SATURDAY": "Samedi",
        "MAX": "Sans jour imposé",
    }[day]


def period_label(period: str) -> str:
    return {
        "MORN": "Matin, de 4 h à 10 h",
        "DAY": "Journée, de 10 h à 20 h",
        "NITE": "Nuit, de 20 h à 4 h",
        "MAX": "Sans période imposée",
    }[period]


def gym_appointment_allowed(
    weekday: str,
    period: str,
    expected_day: str,
    expected_period: str,
    badges: int,
    registered: bool,
    same_map: bool,
    pending: bool,
) -> bool:
    return (
        badges >= 16
        and registered
        and not same_map
        and not pending
        and weekday == expected_day
        and period == expected_period
    )

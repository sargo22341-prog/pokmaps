"""Pokématos HGSS : séries natives et créneaux des contacts, sans Cherche VS."""

import re
from pathlib import Path

from .pret_gen4_source import c_defines, read_json, read_text


def rematch_catalog(root: Path, known: set[int]) -> dict:
    source = "src/overlay_26_022598C0.c"
    text = read_text(root / source)
    body = text.split("sTrainerRematchSets[][6] = {", 1)[1].split("};", 1)[0]
    trainers = c_defines(root / "include/constants/trainers.h", "TRAINER_")
    series = []
    for group in re.findall(r"\{([^{}]+)\}", body):
        names = [name.strip() for name in group.split(",") if name.strip()]
        teams = [trainers[name] for name in names]
        if len(teams) != 6 or any(team and team not in known for team in teams):
            raise ValueError(f"HGSS : série de revanche invalide : {names}")
        series.append(dict(base=teams[0], teams=teams, source=source))
    if len(series) != 63 or len({row["base"] for row in series}) != len(series):
        raise ValueError(f"HGSS : séries de revanches absentes ou répétées : {len(series)}")
    contacts = read_json(root / "files/tel/pmtel_book.json")["pmtel_book"]
    bases = {row["base"] for row in series}
    appointments = []
    for index, row in enumerate(contacts):
        trainer = trainers[row["trainerId"]]
        if trainer and trainer not in known:
            raise ValueError(f"HGSS : contact sans équipe : {row['id']}")
        appointments.append(
            row | dict(index=index, trainer=trainer, rematch=trainer in bases, source="files/tel/pmtel_book.json")
        )
    return dict(
        series=series,
        contacts=appointments,
        engine=source,
        selection_fr="Première équipe non vaincue ; repli au niveau précédent si le groupe est verrouillé.",
        gym_conditions_fr="Numéro enregistré, 16 badges, appel au jour et à la période du contact, "
        "hors de son lieu ; rendez-vous au Dojo après acceptation.",
        gym_engine="src/application/pokegear/phone/scripts/phone_scripts_gym_leader.c",
    )


def select_rematch(teams: list[int], beaten: set[int], unlocked: set[int]) -> int:
    """Reproduit les quatre fonctions de sélection de overlay_26_022598C0.c."""
    if len(teams) != 6 or teams[0] == 0:
        raise ValueError("HGSS : six emplacements de revanche attendus")
    candidate = 5
    for index in range(1, 6):
        if teams[index] == 0:
            candidate = index - 1
            break
        if teams[index] != 65535 and teams[index] not in beaten:
            candidate = index
            break
    if candidate and candidate not in unlocked:
        candidate = next((i for i in range(candidate - 1, 0, -1) if teams[i] != 65535), 0)
    return teams[candidate]

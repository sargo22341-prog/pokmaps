"""Catalogues des activités HGSS, lus dans leur moteur propre."""

import re
from pathlib import Path

from .pokewalker_hgss import walker_catalog
from .pret_gen4_source import read_json, read_json_list, read_text
from .sources import DATA_DIR


def activity_catalog(root: Path, characters: dict, encounters: dict) -> dict:
    editorial = read_json_list(DATA_DIR / "hgss_activities.json")
    if not 1 <= len(editorial) <= 32:
        raise ValueError("HGSS : nombre d'activités hors limite")
    for row in editorial:
        for source in row["sources"]:
            if not (root / source).is_file():
                raise ValueError(f"HGSS : source d'activité absente : {source}")
    return dict(
        guides=editorial,
        pokeathlon=dict(shops=characters["athlete_shops"], courses=_athlon_courses(root)),
        apricorns=characters["apricorns"],
        aprijuice=_aprijuice(root),
        safari=encounters["special_wild"]["safari"],
        safari_maturation=encounters["special_wild"]["maturation_fr"],
        contest=encounters["special_wild"]["contest"],
        pokewalker=walker_catalog(root),
        photos=_photos(root),
        voltorb_flip=_voltorb(root),
        tutors=characters["tutors"],
        services=characters["services"],
        external=encounters["obtainings"],
    )


def _aprijuice(root: Path) -> dict:
    source = "asm/unk_02031B0C.s"
    body = read_text(root / source).split("\n_020F68DE:", 1)[1].split("\n_020F6902:", 1)[0]
    values = [int(v) for line in body.splitlines() if ".byte" in line for v in re.findall(r"-?\d+", line)]
    if len(values) != 36 or values[-1] != 0 or any(v not in (-2, 0, 2, 4) for v in values):
        raise ValueError("HGSS : contributions des Noigrumes à boire invalides")
    colors = ("RED", "YLW", "BLU", "GRN", "PNK", "WHT", "BLK")
    return dict(
        source=source,
        table="_020F68DE",
        mixing_function="sub_02032354",
        contributions=[
            dict(color=f"APRICORN_{color}", native_axes=values[i * 5 : i * 5 + 5]) for i, color in enumerate(colors)
        ],
        rule_fr="Contributions initiales dans l’ordre des cinq axes du moteur ; les bornes, "
        "les saveurs dominantes et la qualité du mélange interviennent ensuite. "
        "Ces nombres ne sont pas les performances finales du Pokémon.",
    )


def _athlon_courses(root: Path) -> dict:
    source = "asm/overlay_96.s"
    text = read_text(root / source)
    tables = {}
    for label, end in (("ov96_0221A934", "ov96_0221A95C"), ("ov96_0221A95C", "sPokeathlonStateInfoFuncTable")):
        body = text.split(f"\n{label}:", 1)[1].split(f"\n{end}:", 1)[0]
        values = [
            int(v, 16) for line in body.splitlines() if ".byte" in line for v in re.findall(r"0x([\da-fA-F]{2})", line)
        ]
        if len(values) != 40 or any(n > 10 for n in values):
            raise ValueError(f"HGSS : table de parcours Pokéathlon invalide : {label}")
        tables[label] = [values[i : i + 4] for i in range(0, 40, 4)]
    return dict(source=source, selector="ov96_021E811C", native_tables=tables)


def _photos(root: Path) -> dict:
    source = "files/data/photo_data.json"
    rows = read_json(root / source)["photos"]
    if not 1 <= len(rows) <= 256 or any(not str(r["map"]).startswith("MAP_") for r in rows):
        raise ValueError("HGSS : catalogue photographique invalide")
    return dict(source=source, sites=[dict(index=i, **row) for i, row in enumerate(rows)])


def _voltorb(root: Path) -> dict:
    source = "src/voltorb_flip/voltorb_flip_game.c"
    body = read_text(root / source).split("sBoardConfigs[80] = {", 1)[1].split("\n};", 1)[0]
    rows = [list(map(int, re.findall(r"\d+", r))) for r in re.findall(r"\{([^{}]+)\}", body)]
    if len(rows) != 80 or any(len(r) != 5 or sum(r[:3]) > 25 for r in rows):
        raise ValueError("HGSS : quatre-vingts configurations Voltorbataille attendues")
    return dict(
        source=source,
        configurations=[
            dict(
                index=i,
                level=i // 10 + 1,
                voltorbs=r[0],
                twos=r[1],
                threes=r[2],
                max_free_row_column=r[3],
                max_free_total=r[4],
                payout=2 ** r[1] * 3 ** r[2],
            )
            for i, r in enumerate(rows)
        ],
    )

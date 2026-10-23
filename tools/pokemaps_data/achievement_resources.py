"""Ressources Android des succès, produites depuis les archives et traductions relues."""

import csv
import hashlib
import json
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from .sources import DATA_DIR


@dataclass(frozen=True)
class _Achievement:
    identifier: int
    title: str
    description: str
    points: int
    missable: bool
    chapter: str


def _translations() -> dict[int, tuple[int, list[dict[str, str]]]]:
    versions: dict[int, tuple[int, list[dict[str, str]]]] = {}
    for filename in ("gen12_fr.csv", "gen3_fr.csv", "gen4_fr.csv", "hgss_fr.csv"):
        with (DATA_DIR / "retroachievements" / filename).open(encoding="utf-8", newline="") as source:
            for row in csv.DictReader(source):
                version, game = int(row["version_id"]), int(row["game_id"])
                selected = versions.setdefault(version, (game, []))
                if selected[0] != game:
                    raise ValueError(f"{filename} : plusieurs ensembles pour la version {version}")
                selected[1].append(row)
    return versions


def _achievements(game: int, translations: list[dict[str, str]]) -> list[_Achievement]:
    archive = json.loads((DATA_DIR / "retroachievements" / f"{game}.json").read_text(encoding="utf-8"))
    official = {row["ID"]: row for row in archive["achievements"]}
    ids = [int(row["achievement_id"]) for row in translations]
    if len(set(ids)) != len(ids) or set(ids) != set(official):
        raise ValueError(f"Traductions absentes ou répétées pour l'ensemble {game}")
    result = []
    for row in translations:
        identifier = int(row["achievement_id"])
        if not all(row[key].strip() for key in ("title_fr", "description_fr", "chapter")):
            raise ValueError(f"Traduction incomplète : {game}:{identifier}")
        entry = official[identifier]
        result.append(
            _Achievement(
                identifier,
                row["title_fr"],
                row["description_fr"],
                entry["Points"],
                entry["type"] == "missable",
                row["chapter"],
            )
        )
    return result


def hgss_achievements() -> dict:
    folder = DATA_DIR / "retroachievements"
    index = json.loads((folder / "index.json").read_text(encoding="utf-8"))
    for game in (7212, 39076):
        entry = next(row for row in index["games"] if row["game_id"] == game)
        if hashlib.sha256((folder / f"{game}.json").read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError(f"HGSS : archive de succès modifiée : {game}")
    empty = json.loads((folder / "39076.json").read_text(encoding="utf-8"))
    game, rows = _translations()[15]
    if game != 7212 or empty["achievements"]:
        raise ValueError("HGSS : association des archives de succès incorrecte")
    entries = _achievements(game, rows)
    if len(entries) != 136:
        raise ValueError("HGSS : 136 succès officiels attendus")
    return dict(
        game_id=game,
        versions=[15, 16],
        empty_archive=39076,
        entries=[asdict(row) for row in entries],
        scope_fr="Archive publique du 12 octobre 2026 : ensemble commun HeartGold/SoulSilver 7212. "
        "L’entrée SoulSilver 39076 est vide et n’est pas utilisée. La synchronisation de lecture est manuelle. "
        "Les deux cartouches reçoivent la même progression distante ; leur suivi local reste distinct. "
        "Les objectifs RetroAchievements conservent les nombres de l’archive, distincts des objectifs cartouche seule.",
    )


def _text(value: str) -> str:
    return escape(value).replace("'", "\\'").replace('"', '\\"')


def _normalized(value: str) -> str:
    return " ".join(value.replace("\\'", "'").replace('\\"', '"').split())


def _known_strings() -> dict[str, str]:
    resources = DATA_DIR.parents[1] / "app/src/main/res/values"
    known: dict[str, str] = {}
    for path in sorted(resources.glob("*.xml")):
        if path.name.startswith("strings_achievements"):
            continue
        for node in ET.parse(path).getroot().findall("string"):
            text = _normalized("".join(node.itertext()))
            if not text.startswith("@string/"):
                known.setdefault(text, node.attrib["name"])
    return known


def _string(name: str, text: str, known: dict[str, str]) -> str:
    value = _normalized(text)
    if reference := known.get(value):
        return f'    <item name="{name}" type="string">@string/{reference}</item>'
    known[value] = name
    return f'    <string name="{name}">{_text(text)}</string>'


def _resource(version: int, entries: list[_Achievement], known: dict[str, str]) -> str:
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        "<resources>",
        "    <!-- Généré par tools/build_data.py (succès) ; modifier les CSV sources. -->",
    ]
    for entry in entries:
        key = f"ra_{entry.identifier}"
        lines.extend(
            (
                _string(f"{key}_title", entry.title, known),
                _string(f"{key}_text", entry.description, known),
                f'    <array name="{key}">',
                f"        <item>{entry.identifier}</item>",
                f"        <item>@string/{key}_title</item>",
                f"        <item>@string/{key}_text</item>",
                f"        <item>{entry.points}</item>",
                f"        <item>{int(entry.missable)}</item>",
                f"        <item>{_text(entry.chapter)}</item>",
                "    </array>",
            )
        )
    lines.append(f'    <array name="achievements_{version}">')
    lines.extend(f"        <item>@array/ra_{entry.identifier}</item>" for entry in entries)
    return "\n".join((*lines, "    </array>", "</resources>", ""))


def build_achievement_resources(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    known = _known_strings()
    for version, (game, translations) in sorted(_translations().items()):
        entries = _achievements(game, translations)
        (output / f"strings_achievements_{version}.xml").write_text(
            _resource(version, entries, known), encoding="utf-8", newline="\n"
        )
    # Les deux cartouches utilisent le même ensemble : une seule définition par succès.
    shared = _achievements(*_translations()[15])
    (output / "strings_achievements_16.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
        '    <array name="achievements_16">\n'
        + "".join(f"        <item>@array/ra_{entry.identifier}</item>\n" for entry in shared)
        + "    </array>\n</resources>\n",
        encoding="utf-8",
        newline="\n",
    )

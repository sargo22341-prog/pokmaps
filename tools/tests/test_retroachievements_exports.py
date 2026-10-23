"""Vérifie les instantanés publics et leurs traductions sans réseau ni clé API."""

import csv
import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pytest

import export_retroachievements
from export_retroachievements import _MAIN_SERIES, _read_content, _snapshot

_ROOT = Path(__file__).resolve().parents[2]
_EXPORTS = _ROOT / "tools/data/retroachievements"
_SINNOH = {12: (9852, "diamond"), 13: (25369, "pearl"), 14: (11732, "platinum")}
_GBA = {7: (790, "ruby"), 8: (791, "sapphire"), 9: (668, "emerald"), 10: (515, "firered"), 11: (788, "leafgreen")}
_HGSS = {15: (7212, "heartgold")}


def test_snapshot_writer_uses_utf8_and_lf_on_every_platform(tmp_path: Path) -> None:
    path = tmp_path / "snapshot.json"
    export_retroachievements._write(path, {"title": "Pokémon"})
    assert path.read_bytes() == '{\n  "title": "Pokémon"\n}\n'.encode()


def test_public_inventory_is_complete_and_contains_no_account_data() -> None:
    index = json.loads((_EXPORTS / "index.json").read_text(encoding="utf-8"))
    assert len(index["games"]) == 20
    assert sum(row["achievement_count"] for row in index["games"]) == 2100
    assert {row["console"] for row in index["games"]} == {
        "Game Boy",
        "Game Boy Color",
        "Game Boy Advance",
        "Nintendo DS",
    }
    for row in index["games"]:
        path = _EXPORTS / f"{row['game_id']}.json"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        assert set(snapshot) == {"game_id", "title", "console", "source", "exported_at", "achievements"}
        assert snapshot["game_id"] == row["game_id"]
        assert _MAIN_SERIES.fullmatch(snapshot["title"])
        assert len(snapshot["achievements"]) == row["achievement_count"]
        ids = [achievement["ID"] for achievement in snapshot["achievements"]]
        assert len(ids) == len(set(ids))
        for achievement in snapshot["achievements"]:
            assert set(achievement) == {"ID", "Title", "Description", "Points", "DisplayOrder", "type", "DateModified"}
            assert achievement["ID"] > 0 and achievement["Points"] >= 0


@pytest.mark.parametrize("version", _GBA | _SINNOH | _HGSS)
def test_translations_and_android_definitions_match_official_snapshot(version: int) -> None:
    game_id, _name = (_GBA | _SINNOH | _HGSS)[version]
    snapshot = json.loads((_EXPORTS / f"{game_id}.json").read_text(encoding="utf-8"))
    filename = "hgss_fr.csv" if version in _HGSS else "gen4_fr.csv" if version in _SINNOH else "gen3_fr.csv"
    with (_EXPORTS / filename).open(encoding="utf-8", newline="") as source:
        translations = [row for row in csv.DictReader(source) if int(row["version_id"]) == version]
    official = {row["ID"]: row for row in snapshot["achievements"]}
    assert {int(row["achievement_id"]) for row in translations} == set(official)
    texts = {
        row.attrib["name"]: row.text
        for path in (_ROOT / "app/src/main/res/values").glob("*.xml")
        for row in ET.parse(path).getroot()
        if row.tag == "string" or (row.tag == "item" and row.attrib.get("type") == "string")
    }
    resource = ET.parse(_ROOT / f"app/src/main/res/values/strings_achievements_{version}.xml").getroot()
    definitions = {
        int(row.attrib["name"].removeprefix("ra_")): list(row)
        for row in resource.findall("array")
        if row.attrib["name"].startswith("ra_")
    }
    assert set(definitions) == set(official)
    for identifier, fields in definitions.items():
        source = official[identifier]
        assert int(fields[0].text) == identifier
        assert int(fields[3].text) == source["Points"]
        assert bool(int(fields[4].text)) == (source["type"] == "missable")
    for row in translations:
        identifier = row["achievement_id"]
        assert int(row["game_id"]) == game_id
        assert _resource(texts, f"ra_{identifier}_title") == row["title_fr"]
        assert _resource(texts, f"ra_{identifier}_text") == row["description_fr"]
        assert row["title_fr"] and row["description_fr"]
        assert definitions[int(identifier)][5].text == row["chapter"]


def _resource(texts: dict[str, str | None], name: str) -> str:
    value = texts[name]
    assert value is not None
    if value.startswith("@string/"):
        value = texts[value.removeprefix("@string/")]
    assert value is not None and not value.startswith("@string/")
    return " ".join(value.replace("\\'", "'").replace('\\"', '"').split())


def _game() -> dict[str, Any]:
    return {
        "ID": 790,
        "ParentGameID": None,
        "Title": "Pokémon Ruby Version",
        "ConsoleName": "Game Boy Advance",
        "NumAchievements": 1,
        "Achievements": {
            "1": {
                "ID": 1,
                "Title": "Titre",
                "Description": "Condition",
                "Points": 0,
                "DisplayOrder": 1,
                "type": None,
                "DateModified": "2026-10-12",
                "DateEarned": "privé",
                "User": "privé",
            }
        },
        "Username": "privé",
    }


def test_snapshot_keeps_zero_point_achievements_and_discards_private_fields() -> None:
    result = _snapshot(_game(), "2026-10-12")
    assert result["achievements"][0]["Points"] == 0
    assert "privé" not in json.dumps(result)


@pytest.mark.parametrize(
    "field,value", [("ID", -1), ("ID", True), ("Points", -1), ("Points", 0.5), ("Description", ""), ("type", "unknown")]
)
def test_invalid_achievement_stops_export(field: str, value: int | float | str) -> None:
    game = _game()
    game["Achievements"]["1"][field] = value
    with pytest.raises(ValueError, match="Succès invalide : 790"):
        _snapshot(game, "2026-10-12")


def test_incomplete_snapshot_stops_export() -> None:
    game = _game()
    game["NumAchievements"] = 2
    with pytest.raises(ValueError, match="Nombre de succès invalide : 790"):
        _snapshot(game, "2026-10-12")


def test_all_sync_game_ids_point_to_public_main_sets_with_shared_hgss() -> None:
    path = _ROOT / "app/src/main/java/org/opensources/pokmaps/domain/guide/RetroProgress.kt"
    mapping = {int(version): int(game) for version, game in re.findall(r"(\d+) to (\d+)", path.read_text())}
    assert set(mapping) == set(range(1, 17))
    assert len(set(mapping.values())) == 15
    assert mapping[15] == mapping[16] == 7212
    assert 39076 not in mapping.values()
    assert {version: mapping[version] for version in _GBA} == {version: game for version, (game, _) in _GBA.items()}
    for game in mapping.values():
        assert json.loads((_EXPORTS / f"{game}.json").read_text(encoding="utf-8"))["game_id"] == game


def test_download_size_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(export_retroachievements, "_MAX_BYTES", 8)
    assert _read_content(io.BytesIO(b"12345678")) == b"12345678"
    with pytest.raises(ValueError, match="réponse trop grande"):
        _read_content(io.BytesIO(b"123456789"))

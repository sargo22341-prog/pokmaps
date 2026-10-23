"""Preuves de qualification HGSS et séparation des générations distribuées."""

import csv
import hashlib
import json
import struct
from pathlib import Path

import pytest

from pokemaps_data.games import ALL_GAMES, DECLARED_GAMES, GAMES, GAMES_IN_PROGRESS, PretFormat
from pokemaps_data.hgss_preparation import HEARTGOLD_SOULSILVER, PREPARATORY_GAMES
from pokemaps_data.pret_gen4 import Gen4PretRepo
from pokemaps_data.sources import HGSS_PRET_COMMIT, POKEAPI_COMMIT, PRET_COMMITS

_ROOT = Path(__file__).resolve().parents[2]
_INVENTORY = json.loads((_ROOT / "docs/generations/sources-hgss.json").read_text(encoding="utf-8"))


def test_qualified_hgss_contract_is_in_the_active_catalog() -> None:
    game = HEARTGOLD_SOULSILVER
    assert not PREPARATORY_GAMES
    assert game.pret_versions == (("heartgold", "HEARTGOLD"), ("soulsilver", "SOULSILVER"))
    assert game.version_group == game.map_family == "heartgold-soulsilver"
    assert game.pret_format == PretFormat.GEN4
    assert game.national_dex and game.remake_generation == 2
    assert [(r.const, r.start_map, r.number) for r in game.regions] == [
        ("JOHTO", "NEW_BARK", 993),
        ("KANTO", "PALLET", 992),
    ]
    for games in (GAMES, ALL_GAMES, DECLARED_GAMES):
        assert game in games
    assert game not in GAMES_IN_PROGRESS
    assert sum(len(g.pret_versions) for g in GAMES) == 16
    assert PRET_COMMITS["pokeheartgold"] == HGSS_PRET_COMMIT
    assert _INVENTORY["pret_commit"] == HGSS_PRET_COMMIT
    assert _INVENTORY["pokeapi_commit"] == POKEAPI_COMMIT
    current_regions = {r.number for g in DECLARED_GAMES if g != game for r in g.regions}
    assert not current_regions & {r.number for r in game.regions}


def test_sinnoh_reader_rejects_preparatory_versions() -> None:
    with pytest.raises(ValueError, match="versions DS invalides"):
        Gen4PretRepo(_ROOT, HEARTGOLD_SOULSILVER.pret_versions)


def test_local_achievement_evidence_and_shared_set() -> None:
    root = _ROOT / "tools/data/retroachievements"
    _assert_hashes(root, _INVENTORY["local_files"])
    common = json.loads((root / "7212.json").read_text(encoding="utf-8"))
    empty = json.loads((root / "39076.json").read_text(encoding="utf-8"))
    assert common["game_id"] == 7212 and len(common["achievements"]) == 136
    assert empty["game_id"] == 39076 and empty["achievements"] == []
    assert len({row["ID"] for row in common["achievements"]}) == 136


def _assert_hashes(root: Path, expected: dict[str, str]) -> None:
    for name, digest in expected.items():
        path = root / name
        assert path.is_file(), f"Source qualifiée absente : {path}"
        data = path.read_bytes()
        if path.suffix in {".md", ".h", ".c", ".inc", ".json", ".txt", ".csv", ".MIT"}:
            data = data.replace(b"\r\n", b"\n")
        assert hashlib.sha256(data).hexdigest() == digest, f"Source qualifiée modifiée : {path}"


def _csv_rows(root: Path, name: str) -> list[dict[str, str]]:
    with (root / f"{name}.csv").open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _native_johto_ranks(path: Path) -> dict[int, int]:
    data = path.read_bytes()
    assert data[:4] == b"NARC", path
    offset = 16
    member_start = member_end = None
    for _ in range(3):
        tag, size = struct.unpack_from("<4sI", data, offset)
        assert 8 <= size <= len(data) - offset, path
        if tag == b"BTAF":
            assert struct.unpack_from("<H", data, offset + 8)[0] == 1, path
            member_start, member_end = struct.unpack_from("<II", data, offset + 12)
        if tag == b"GMIF":
            assert member_start is not None and member_end is not None, path
            member = data[offset + 8 + member_start : offset + 8 + member_end]
            assert len(member) == 494 * 2, path
            return {species: rank for species, rank in enumerate(struct.unpack("<494H", member)) if rank}
        offset += size
    raise AssertionError(f"Table régionale HGSS absente : {path}")


@pytest.mark.pipeline
def test_pinned_native_sources_and_pokeapi_agree() -> None:
    cache = _ROOT / "tools/.cache"
    native = cache / "hgss-qualification"
    api = cache / f"pokeapi-{POKEAPI_COMMIT[:12]}"
    _assert_hashes(native, _INVENTORY["pret_files"])
    _assert_hashes(api, _INVENTORY["pokeapi_files"])
    versions = [r for r in _csv_rows(api, "versions") if r["version_group_id"] == "10"]
    assert [(r["id"], r["identifier"]) for r in versions] == [("15", "heartgold"), ("16", "soulsilver")]
    group = next(r for r in _csv_rows(api, "version_groups") if r["id"] == "10")
    assert (group["identifier"], group["generation_id"]) == ("heartgold-soulsilver", "4")
    french = {r["version_id"]: r["name"] for r in _csv_rows(api, "version_names") if r["local_language_id"] == "5"}
    assert (french["15"], french["16"]) == ("Or HeartGold", "Argent SoulSilver")
    ranks = {
        int(r["species_id"]): int(r["pokedex_number"])
        for r in _csv_rows(api, "pokemon_dex_numbers")
        if r["pokedex_id"] == "7"
    }
    assert sorted(ranks.values()) == list(range(1, 257))
    assert _native_johto_ranks(native / "files/poketool/johtozukan.narc") == ranks
    assert all(1 <= species <= 493 for species in ranks)


@pytest.mark.pipeline
@pytest.mark.parametrize(
    ("folder", "pattern", "count"),
    [
        ("fielddata/mapmatrix/map_matrix", "*.bin", "matrices"),
        ("fielddata/eventdata/zone_event", "*.json", "event_tables"),
        ("fielddata/script/scr_seq", "*.s", "scripts"),
        ("fielddata/script/scr_seq", "*.h", "script_headers"),
        ("msgdata/msg", "*.json", "message_banks"),
    ],
)
def test_source_catalog_counts(folder: str, pattern: str, count: str) -> None:
    root = _ROOT / "tools/.cache/hgss-qualification/files" / folder
    assert root.is_dir(), f"Source qualifiée absente : {root}"
    assert len(list(root.glob(pattern))) == _INVENTORY["counts"][count]


@pytest.mark.pipeline
@pytest.mark.parametrize(
    ("path", "key", "count"),
    [
        ("fielddata/encountdata/gs_enc_data.json", "encounters", "wild_tables"),
        ("arc/headbutt.json", "tables", "headbutt_tables"),
        ("arc/safari_enc.json", "encounters", "safari_areas"),
        ("poketool/personal/personal.json", "baseStats", "personal_entries"),
        ("poketool/personal/evo.json", "evoTable", "evolution_entries"),
        ("poketool/trainer/trainers.json", "trainers", "trainers"),
    ],
)
def test_source_table_counts(path: str, key: str, count: str) -> None:
    source = _ROOT / "tools/.cache/hgss-qualification/files" / path
    data = json.loads(source.read_text(encoding="utf-8"))
    assert len(data[key]) == _INVENTORY["counts"][count]

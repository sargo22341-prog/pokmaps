"""Une candidate ne peut modifier ni une donnée antérieure ni un asset livré."""

import hashlib
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from pokemaps_data.candidate_hgss import qualify, validate_destination


def _assets(path: Path, value: str, data: bytes = b"old") -> Path:
    (path / "database").mkdir(parents=True)
    with closing(sqlite3.connect(path / "database/pokedex.db")) as connection:
        connection.execute("CREATE TABLE version (id INTEGER PRIMARY KEY, name TEXT)")
        connection.execute("INSERT INTO version VALUES (1, ?)", (value,))
        connection.execute("INSERT INTO version VALUES (2, 'HGSS')")
        connection.commit()
    (path / "map.webp").write_bytes(data)
    (path / "assets.sha256").write_text(hashlib.sha256(data).hexdigest() + "  map.webp\n", encoding="utf-8")
    return path


def test_candidate_preserves_existing_data_and_assets(tmp_path: Path) -> None:
    previous = _assets(tmp_path / "previous", "Rouge")
    candidate = _assets(tmp_path / "candidate", "Rouge")
    assert qualify(previous, candidate) == (2, 1)


def test_candidate_rejects_an_existing_row_change(tmp_path: Path) -> None:
    previous = _assets(tmp_path / "previous", "Rouge")
    candidate = _assets(tmp_path / "candidate", "Incorrect")
    with pytest.raises(ValueError, match="version"):
        qualify(previous, candidate)


def test_candidate_rejects_an_existing_asset_change(tmp_path: Path) -> None:
    previous = _assets(tmp_path / "previous", "Rouge")
    candidate = _assets(tmp_path / "candidate", "Rouge", b"changed")
    with pytest.raises(ValueError, match=r"map\.webp"):
        qualify(previous, candidate)


def test_candidate_rejects_a_preexisting_technical_preview(tmp_path: Path) -> None:
    target = tmp_path / "candidate"
    (target / "hgss-maps").mkdir(parents=True)
    with pytest.raises(ValueError, match="hors livraison"):
        validate_destination(tmp_path / "assets", target)


@pytest.mark.parametrize("relative", ("assets/candidate", "."))
def test_candidate_cannot_contain_or_belong_to_distributed_assets(tmp_path: Path, relative: str) -> None:
    with pytest.raises(ValueError, match="séparée"):
        validate_destination(tmp_path / "assets", tmp_path / relative)


def test_candidate_accepts_a_fresh_destination(tmp_path: Path) -> None:
    validate_destination(tmp_path / "assets", tmp_path / "candidate")

"""Empreintes HGSS identiques entre les sources texte Windows et Linux."""

import hashlib
from pathlib import Path

import pytest

from pokemaps_data.sources_characters_hgss import source_digest


@pytest.mark.parametrize("suffix", [".c", ".h", ".s", ".csv", ".json", ".py"])
def test_text_digest_normalizes_line_endings(tmp_path: Path, suffix: str) -> None:
    source = tmp_path / f"source{suffix}"
    unix = b"first\nsecond\n"
    source.write_bytes(unix)
    expected = source_digest(source)
    source.write_bytes(unix.replace(b"\n", b"\r\n"))
    assert source_digest(source) == expected == hashlib.sha256(unix).hexdigest()
    source.write_bytes(b"modified\nsecond\n")
    assert source_digest(source) != expected


def test_binary_digest_preserves_line_ending_bytes(tmp_path: Path) -> None:
    source = tmp_path / "source.narc"
    data = b"first\r\nsecond\r\n"
    source.write_bytes(data)
    assert source_digest(source) == hashlib.sha256(data).hexdigest()

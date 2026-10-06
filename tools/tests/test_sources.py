from __future__ import annotations

import stat
from io import BytesIO
from pathlib import Path

import pytest

from pokemaps_data import sources


class FakeResponse(BytesIO):
    def __init__(self, content: bytes, content_length: str | None = None) -> None:
        super().__init__(content)
        self.headers = {} if content_length is None else {"Content-Length": content_length}

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def test_download_streams_and_atomically_caches_content(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "source.csv"
    monkeypatch.setattr(sources.urllib.request, "urlopen", lambda *_args, **_kwargs: FakeResponse(b"abc", "3"))

    assert sources.download("https://example.test/source.csv", target)

    assert target.read_bytes() == b"abc"
    assert not target.with_name(target.name + ".tmp").exists()


def test_download_rejects_oversized_response_and_removes_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "source.csv"
    monkeypatch.setattr(sources, "MAX_DOWNLOAD_BYTES", 3)
    monkeypatch.setattr(sources.urllib.request, "urlopen", lambda *_args, **_kwargs: FakeResponse(b"abcd"))

    with pytest.raises(ValueError, match="Ressource trop volumineuse"):
        sources.download("https://example.test/source.csv", target)

    assert not target.exists()
    assert not target.with_name(target.name + ".tmp").exists()


def test_remove_tree_handles_read_only_git_files(tmp_path: Path) -> None:
    target = tmp_path / "source"
    target.mkdir()
    read_only = target / "pack.idx"
    read_only.write_bytes(b"git pack index")
    read_only.chmod(stat.S_IREAD)

    sources._remove_tree(target)

    assert not target.exists()

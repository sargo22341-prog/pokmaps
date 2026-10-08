from __future__ import annotations

import http.client
import stat
import urllib.error
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


@pytest.mark.parametrize("failure", [urllib.error.URLError(ConnectionResetError("reset")), TimeoutError("timeout")])
def test_download_retries_network_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: Exception) -> None:
    calls: list[str] = []
    delays: list[float] = []

    def open_response(url: str, *, timeout: int) -> FakeResponse:
        assert timeout == sources.DOWNLOAD_TIMEOUT_SECONDS
        calls.append(url)
        if len(calls) == 1:
            raise failure
        return FakeResponse(b"complete")

    monkeypatch.setattr(sources.urllib.request, "urlopen", open_response)
    monkeypatch.setattr(sources.time, "sleep", delays.append)
    target = tmp_path / "source.csv"
    assert sources.download("https://example.test/source.csv", target)
    assert target.read_bytes() == b"complete"
    assert len(calls) == 2
    assert delays == [1]


@pytest.mark.parametrize("status", [404, 403, 429, 503])
def test_download_handles_http_failures_with_bounded_retries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    calls: list[str] = []
    delays: list[float] = []
    target = tmp_path / "source.csv"
    temporary = target.with_name(target.name + ".tmp")

    def fail_response(url: str, *, timeout: int) -> FakeResponse:
        calls.append(url)
        temporary.write_bytes(b"partial")
        raise urllib.error.HTTPError(url, status, "failure", None, None)

    monkeypatch.setattr(sources.urllib.request, "urlopen", fail_response)
    monkeypatch.setattr(sources.time, "sleep", delays.append)
    url = "https://example.test/source.csv"
    if status == 404:
        assert not sources.download(url, target)
    elif status == 403:
        with pytest.raises(urllib.error.HTTPError):
            sources.download(url, target)
    else:
        with pytest.raises(RuntimeError, match=url) as failure:
            sources.download(url, target)
        assert isinstance(failure.value.__cause__, urllib.error.HTTPError)
    assert len(calls) == (4 if status in (429, 503) else 1)
    assert delays == ([1, 2, 4] if status in (429, 503) else [])
    assert not target.exists()
    assert not temporary.exists()


def test_download_restarts_after_interrupted_response(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "source.csv"
    temporary = target.with_name(target.name + ".tmp")
    calls: list[str] = []

    class InterruptedResponse(FakeResponse):
        def read(self, size: int = -1) -> bytes:
            if self.tell():
                raise http.client.IncompleteRead(b"partial", 10)
            return super().read(size)

    def open_response(url: str, *, timeout: int) -> FakeResponse:
        assert not temporary.exists()
        calls.append(url)
        return InterruptedResponse(b"partial") if len(calls) == 1 else FakeResponse(b"complete")

    monkeypatch.setattr(sources.urllib.request, "urlopen", open_response)
    monkeypatch.setattr(sources.time, "sleep", lambda _delay: None)
    assert sources.download("https://example.test/source.csv", target)
    assert target.read_bytes() == b"complete"
    assert len(calls) == 2
    assert not temporary.exists()

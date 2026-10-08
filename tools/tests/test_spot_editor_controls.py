"""Coordonnées, zoom et navigation de l'éditeur sans ouvrir de fenêtre visible."""

import json
import tkinter as tk
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from pokemaps_data.map_spots import Point, TerrainKey
from spot_editor import app
from spot_editor.canvas import SpotCanvas
from spot_editor.catalog import EditorMap, Family
from spot_editor.error_panel import ErrorPanel
from spot_editor.session import SpotSession
from spot_editor.validation import SpotError, spot_errors, write_errors
from spot_editor.viewport import MapViewport

ROUTE = EditorMap("red-blue-yellow", "route-1", "Route 1", "red-blue", (1012,), "kanto", 800, 3168, 320, 576)
KEY = TerrainKey(ROUTE.family, ROUTE.identifier, "grass")
FAMILY = Family(KEY.family, "Rouge, Bleu et Jaune", ("red-blue", "yellow"))
VALID = (808, 3176)
INVALID = (824, 3192)


class LocalTerrains:
    def rejected_versions(self, _family: Family, _identifier: str, _kind: str, _point: Point) -> tuple[str, ...]:
        return ("Rouge/Bleu",)

    def kinds(self, _family: Family, _identifier: str) -> frozenset[str]:
        return frozenset({"grass"})

    def points(self, _family: Family, _identifier: str, _kind: str) -> frozenset[Point]:
        return frozenset({VALID})

    def region(self, _family: Family, _identifier: str) -> str:
        return "kanto"


@pytest.fixture
def window() -> Iterator[tk.Tk]:
    root = tk.Tk()
    root.withdraw()
    try:
        yield root
    finally:
        root.destroy()


def test_viewport_coordinates_survive_zoom_focus_and_pan() -> None:
    view = MapViewport()
    view.change_zoom(4)
    view.focus(ROUTE, INVALID)
    view.layout(ROUTE, 640, 480)
    assert view.screen(ROUTE, INVALID) == (320, 240)
    view.pan(30, -40, ROUTE)
    view.layout(ROUTE, 640, 480)
    screen = view.screen(ROUTE, VALID)
    assert view.map_point(ROUTE, *screen) == pytest.approx(VALID)


def test_zoom_is_bounded() -> None:
    view = MapViewport()
    view.change_zoom(1000)
    assert view.zoom == 16
    view.change_zoom(0.00001)
    assert view.zoom == 0.25


def test_collects_all_errors_and_persists_report(tmp_path: Path) -> None:
    other = TerrainKey(KEY.family, "route-2", "water")
    session = SpotSession({KEY: frozenset({VALID, INVALID, (840, 3208)}), other: frozenset()})
    errors = spot_errors(session, [FAMILY], LocalTerrains())
    assert len(errors) == 3
    assert [item.point for item in errors] == [INVALID, (840, 3208), None]
    report = tmp_path / "build/errors.json"
    write_errors(errors, report)
    assert len(json.loads(report.read_text(encoding="utf-8"))) == 3
    session.remove(KEY, frozenset(), INVALID)
    assert session.points(KEY, frozenset()) == {VALID, (840, 3208)}
    assert len(spot_errors(session, [FAMILY], LocalTerrains())) == 2
    write_errors([], report)
    assert json.loads(report.read_text(encoding="utf-8")) == []


def test_error_panel_navigates_and_removes_selected_point(window: tk.Tk) -> None:
    selected: list[SpotError] = []
    removed: list[SpotError] = []
    panel = ErrorPanel(window, selected.append, removed.append)
    error = SpotError(KEY, INVALID, "Hors du terrain")
    panel.show([error])
    panel.list.selection_set(0)
    panel._select(SimpleNamespace())
    panel._remove()
    assert selected == removed == [error]
    panel.show([])
    panel._remove()
    assert removed == [error]


def test_canvas_reports_map_coordinates_and_keeps_zoom_on_edit(window: tk.Tk, monkeypatch: pytest.MonkeyPatch) -> None:
    clicks: list[tuple[float, float]] = []
    canvas = SpotCanvas(window, lambda x, y, _hit: clicks.append((x, y)))
    monkeypatch.setattr(canvas.canvas, "winfo_width", lambda: 640)
    monkeypatch.setattr(canvas.canvas, "winfo_height", lambda: 480)
    image = Image.new("RGBA", (320, 576))
    canvas.show(ROUTE, image, frozenset({VALID}))
    canvas.zoom(2)
    canvas.view.layout(ROUTE, 640, 480)
    x, y = canvas.view.screen(ROUTE, VALID)
    event = SimpleNamespace(x=x, y=y)
    canvas._motion(event)
    canvas._click(event)
    assert "x=808, y=3176" in canvas.coordinates.cget("text")
    assert "Case : 808, 3176" in canvas.coordinates.cget("text")
    assert clicks == [pytest.approx(VALID)]
    canvas._wheel(SimpleNamespace(x=x, y=y, delta=120))
    assert canvas.view.map_point(ROUTE, x, y) == pytest.approx(VALID)
    assert canvas._photo.width() == 640
    assert canvas._photo.height() == 480
    canvas.show(ROUTE, image, frozenset())
    assert canvas.view.zoom == 2.5
    canvas.reset()
    assert canvas.view.zoom == 1


def test_editor_opens_error_location_and_updates_report(
    window: tk.Tk, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = tmp_path / "errors.json"
    monkeypatch.setattr(app, "ERROR_REPORT", report)
    monkeypatch.setattr(app, "WildTerrains", lambda _cache: LocalTerrains())
    monkeypatch.setattr(app, "read_spots", lambda: {KEY: frozenset({INVALID})})
    editor = app.MapEditor(window)
    try:
        [error] = editor.errors
        editor._save()
        assert "1 erreur(s)" in editor.status.cget("text")
        editor._go_to_error(error)
        assert editor.current.identifier == "route-1"
        assert editor._kind() == "grass"
        assert editor.canvas.view.center == (INVALID[0] - editor.current.x, INVALID[1] - editor.current.y)
        editor._remove_error(error)
        assert editor.errors == []
        assert editor.session.has_changes
        assert json.loads(report.read_text(encoding="utf-8")) == []
    finally:
        editor.catalog.close()


@pytest.mark.parametrize(
    ("family_id", "groups"),
    [
        ("red-blue-yellow", ("red-blue", "yellow")),
        ("gold-silver-crystal", ("gold-silver", "crystal")),
    ],
)
def test_editor_switches_map_and_selects_matching_point_scope(
    window: tk.Tk, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, family_id: str, groups: tuple[str, str]
) -> None:
    monkeypatch.setattr(app, "ERROR_REPORT", tmp_path / "errors.json")
    monkeypatch.setattr(app, "WildTerrains", lambda _cache: LocalTerrains())
    monkeypatch.setattr(app, "read_spots", dict)
    editor = app.MapEditor(window)
    try:
        index = next(i for i, family in enumerate(editor.families) if family.identifier == family_id)
        editor.family_choice.current(index)
        editor._choose_family()
        identifier = editor.current.identifier
        old_id = editor.current.map_ids[0]
        editor.version_choice.only_displayed.set(False)
        editor.version_choice.choice.current(1)
        editor.version_choice._changed(SimpleNamespace())
        assert editor.current.identifier == identifier
        assert editor.current.version_group == groups[1]
        assert editor.current.map_ids[0] != old_id
        assert editor.version_choice.only_displayed.get()
        assert editor._key("grass").version_group == groups[1]
        editor.version_choice.only_displayed.set(False)
        assert editor._key("grass").version_group == ""
        editor.version_choice.choice.current(0)
        editor.version_choice._changed(SimpleNamespace())
        assert editor.current.version_group == groups[0]
        assert editor._key("grass").version_group == groups[0]
    finally:
        editor.catalog.close()


def test_editor_adds_a_point_only_for_the_displayed_group(
    window: tk.Tk, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(app, "ERROR_REPORT", tmp_path / "errors.json")
    monkeypatch.setattr(app, "WildTerrains", lambda _cache: LocalTerrains())
    monkeypatch.setattr(app, "read_spots", dict)
    editor = app.MapEditor(window)
    try:
        editor._load_family("route-1")
        editor.generated = {kind: frozenset() for kind in ("grass", "floor", "water", "tree", "rock")}
        editor._click(*VALID, lambda _point: False)
        key = TerrainKey(KEY.family, KEY.map_identifier, KEY.kind, "red-blue")
        assert editor.session.merged() == {key: frozenset({VALID})}
        editor.version_choice.choice.current(1)
        editor.version_choice._changed(SimpleNamespace())
        assert editor.session.merged() == {key: frozenset({VALID})}
        assert editor._key("grass").version_group == "yellow"
    finally:
        editor.catalog.close()

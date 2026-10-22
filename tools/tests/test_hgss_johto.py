"""Frontières, plans et inventaire HGSS : fixtures locales sans sources téléchargées."""

import csv
import json
from dataclasses import asdict, replace
from pathlib import Path

import pytest
from PIL import Image

from pokemaps_data import preview_johto_hgss, preview_maps_hgss
from pokemaps_data.catalog_maps_hgss import HgssMapEntry, passage_catalog, read_catalog, validate_catalog_geometry
from pokemaps_data.maps_plans_hgss import plan_layout, write_plan
from pokemaps_data.maps_render_hgss import HgssRenderer
from pokemaps_data.maps_review_hgss import write_johto_review
from pokemaps_data.pret_hgss_maps import HgssEvents, HgssHeader, HgssMapRepo, HgssWarp, _warp
from pokemaps_data.preview_johto_hgss import _render, validate_johto_output
from pokemaps_data.sources import HGSS_PRET_COMMIT


class _Repo(HgssMapRepo):
    def __init__(self) -> None:
        super().__init__(Path("fixture"), "heartgold")
        self._headers = {i: HgssHeader(i, f"MAP_TEST_{i}", 0, 0, i, ()) for i in range(3)}
        self.warps = {0: (HgssWarp(1, 2, 0, 1, 0),), 1: (HgssWarp(3, 4, 0, 0, 0),), 2: ()}

    @property
    def headers(self) -> dict[int, HgssHeader]:
        return self._headers

    def events(self, header: HgssHeader) -> HgssEvents:
        return HgssEvents("fixture.json", self.warps[header.index], ())

    def blocks(self, header: HgssHeader) -> tuple[tuple[int, int, int, int], ...]:
        return ((0, 0, 0, 0),)


def _entries() -> tuple[HgssMapEntry, ...]:
    return (
        HgssMapEntry(0, "MAP_TEST_0", "johto", "Ville", "ville", "base", ""),
        HgssMapEntry(1, "MAP_TEST_1", "johto", "Maison", "maison", "1f", ""),
        HgssMapEntry(2, "MAP_TEST_2", "kanto", "Autre région", "autre", "base", ""),
    )


def _write_catalog(path: Path, entries: tuple[HgssMapEntry, ...]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=asdict(entries[0]))
        writer.writeheader()
        writer.writerows(asdict(entry) for entry in entries)


def test_editorial_catalog_matches_native_inventory(tmp_path: Path) -> None:
    path = tmp_path / "maps.csv"
    _write_catalog(path, _entries())
    assert read_catalog(_Repo(), path) == _entries()


@pytest.mark.parametrize(
    "field,value", [("name_fr", ""), ("plan", "../oops"), ("scope", "unknown"), ("const", "MAP_MISSING"), ("floor", "")]
)
def test_invalid_editorial_entry_is_named(tmp_path: Path, field: str, value: str) -> None:
    entries = _entries()
    changed = replace(entries[0], **{field: value})
    path = tmp_path / "maps.csv"
    _write_catalog(path, (changed, *entries[1:]))
    with pytest.raises(ValueError, match="MAP_"):
        read_catalog(_Repo(), path)


def test_missing_or_duplicated_native_entry_is_rejected(tmp_path: Path) -> None:
    entries = _entries()
    path = tmp_path / "maps.csv"
    for changed in (entries[:2], (entries[0], entries[0], entries[2])):
        _write_catalog(path, changed)
        with pytest.raises(ValueError, match="incomplet ou dupliqué"):
            read_catalog(_Repo(), path)


def test_passages_keep_return_anchors_and_explicit_boundaries() -> None:
    repo = _Repo()
    repo.warps[2] = (HgssWarp(1, 1, 0, 0, 0),)
    repo.warps[1] += (HgssWarp(1, 1, 0, 2, 0),)
    passages = passage_catalog(repo, _entries())
    assert [p["kind"] for p in passages] == ["fixed", "fixed", "boundary"]
    assert passages[0]["target"]["destination"] == 0
    assert passages[2]["target_scope"] == "kanto"


def test_dynamic_elevator_exit_is_not_a_fictitious_map() -> None:
    repo = _Repo()
    row = {"x": 3, "z": 6, "y": 0, "header": 4095, "anchor": 256}
    repo.warps[0] = (_warp(row, {}, "ascenseur"),)
    passage = passage_catalog(repo, _entries())[0]
    assert passage["kind"] == "variable" and passage["target_scope"] == "memory"
    assert "target" not in passage
    repo.warps[0] = (replace(repo.warps[0][0], anchor=0),)
    with pytest.raises(ValueError, match="destination mémorisée inconnue"):
        passage_catalog(repo, _entries())


def test_broken_anchor_and_warp_outside_geometry_fail() -> None:
    repo = _Repo()
    repo.warps[0] = (HgssWarp(1, 1, 0, 1, 7),)
    with pytest.raises(ValueError, match="ancre 7 absente"):
        passage_catalog(repo, _entries())
    repo.warps[0] = (HgssWarp(100, 1, 0, 1, 0),)
    with pytest.raises(ValueError, match="hors des blocs"):
        validate_catalog_geometry(repo, _entries())


def test_world_layout_preserves_ds_positions_and_atlas_separates_rooms() -> None:
    records = [
        dict(header=0, plan="johto-exterieurs", origin_pixels=(512, 1024), size=(256, 256)),
        dict(header=1, plan="johto-exterieurs", origin_pixels=(1024, 1024), size=(256, 256)),
    ]
    size, parts = plan_layout(records)
    assert size == (768, 256) and parts[1]["offset"] == (512, 0)
    size, parts = plan_layout([{**record, "plan": "maisons"} for record in records])
    assert size == (768, 256) and parts[1]["offset"] == (512, 0)


def test_tiled_assembly_keeps_both_rooms_at_every_zoom(tmp_path: Path) -> None:
    records = []
    for index, color in enumerate(("red", "blue")):
        Image.new("RGBA", (32, 32), color).save(tmp_path / f"{index}.png")
        records.append(
            dict(header=index, plan="maison", size=(32, 32), image=f"{index}.png", name_fr="Maison", floor="1f")
        )
    plan = write_plan(tmp_path, records, tmp_path / "plans/maison")
    with Image.open(tmp_path / f"plans/maison/{plan['level_count'] - 1}/0_1.webp") as tile:
        assert tile.convert("RGBA").getpixel((32, 0)) == (0, 0, 255, 255)
    assert (tmp_path / "plans/maison/0/0_0.webp").is_file()


def test_output_requires_all_selected_maps_and_unique_plan_members(tmp_path: Path) -> None:
    catalog = {"maps": [], "plans": [], "inventory": [asdict(entry) for entry in _entries()], "passages": []}
    with pytest.raises(ValueError, match="lieu ou plan absent"):
        validate_johto_output(tmp_path, catalog)


def _fail_johto(root: Path, output: Path, cache: Path, workers: int) -> dict:
    raise ValueError(f"{root} {output} {cache} {workers} : carte Johto illisible")


def test_failed_johto_generation_preserves_previous_valid_preview(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "preview/hgss-maps"
    target.mkdir(parents=True)
    previous = target / "catalog.json"
    previous.write_text("ancien catalogue valide", encoding="utf-8")
    monkeypatch.setattr(preview_maps_hgss, "validate_sources", lambda root: {})
    monkeypatch.setattr(preview_maps_hgss, "_version", lambda root, output, version: {"maps": [], "proof": {}})
    monkeypatch.setattr(preview_johto_hgss, "build_johto", _fail_johto)
    with pytest.raises(ValueError, match="carte Johto illisible"):
        preview_maps_hgss.build_hgss_maps(tmp_path / "cache", target.parent, 1)
    assert previous.read_text(encoding="utf-8") == "ancien catalogue valide"


def test_modified_render_cache_is_rejected(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "0.png").write_bytes(b"corrompu")
    (cache / "0.json").write_text(json.dumps({"image_sha256": "0" * 64}), encoding="utf-8")
    with pytest.raises(ValueError, match="cache de rendu HGSS modifié"):
        _render(HgssRenderer(_Repo()), asdict(_entries()[0]), tmp_path / "output", cache)


def test_review_accepts_both_rgba_maps_and_rgb_plan_thumbnails(tmp_path: Path) -> None:
    maps = tmp_path / "johto"
    (maps / "maps/0").mkdir(parents=True)
    Image.new("RGBA", (32, 32), "red").save(maps / "maps/0/map.png")
    entry = asdict(_entries()[0])
    entry.update(size=(32, 32), image="maps/0/map.png")
    plan = write_plan(maps, [entry], maps / "plans/ville")
    catalog = {"maps": [entry], "plans": [plan], "inventory": [entry], "passages": [], "commit": "fixture"}
    (maps / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
    output = tmp_path / "review"
    [sheet] = write_johto_review(maps, output)
    with Image.open(sheet) as image:
        assert image.size == (1152, 1408)
        assert image.getpixel((128, 4)) == (255, 0, 0)
    index = json.loads((output / "index.json").read_text(encoding="utf-8"))
    assert [card["kind"] for card in index["cards"]] == ["lieu", "plan"]
    assert index["cards"][0]["image"] == "maps/0/map.png"


def test_versioned_review_covers_every_editorial_map_and_plan() -> None:
    root = Path(__file__).resolve().parents[2]
    report = json.loads((root / "docs/generations/cartes-hgss-johto-preuve.json").read_text(encoding="utf-8"))
    with (root / "tools/data/hgss_maps.csv").open(encoding="utf-8", newline="") as handle:
        entries = [row for row in csv.DictReader(handle) if row["scope"] == "johto"]
    assert report["commit"] == HGSS_PRET_COMMIT
    assert set(report["pixels_sha256"]) == {row["header"] for row in entries}
    assert report["plans"] == len({row["plan"] for row in entries})
    assert report["review_cards"] == len(entries) + report["plans"] + 1
    assert len(report["review_sheets"]) == 24

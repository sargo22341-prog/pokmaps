"""Plans DS : tuiles, régions et deux extrémités des passages changent de repère ensemble."""

from pathlib import Path

import pytest
from PIL import Image

from pokemaps_data import maps_assemblies_gen4
from pokemaps_data.map_spots import TerrainKey
from pokemaps_data.maps import GameMapData, MapRow, SpotRow, WarpRow
from pokemaps_data.maps_assemblies_gen4 import assemble_floors, read_assemblies
from pokemaps_data.maps_characters import ObjectRow
from spot_editor.session import SpotSession


def _data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, overlap: bool = False) -> GameMapData:
    monkeypatch.setattr(maps_assemblies_gen4, "DATA_DIR", tmp_path)
    (tmp_path / "map_assemblies_gen4.csv").write_text(
        "family,plan,number,name_fr,map,x,y\n"
        "platinum,FLOOR_1F,700,Etage,A,0,0\n"
        f"platinum,FLOOR_1F,700,Etage,B,{0 if overlap else 512},0\n",
        encoding="utf-8",
    )
    maps = [MapRow(name, n, name, None, 0, 0, 256, 256, 1) for n, name in enumerate(("A", "B"))]
    for name, color in (("A", "red"), ("B", "blue")):
        folder = tmp_path / name.lower() / "0"
        folder.mkdir(parents=True)
        Image.new("RGBA", (256, 256), color).save(folder / "0_0.webp", "WEBP", lossless=True)
    obj = ObjectRow("B", "npc", 8, 24, "1", None, None, None, None)
    return GameMapData(
        maps,
        [],
        [WarpRow("A", 8, 8, "B", 24, 40), WarpRow("B", 24, 40, "A", 8, 8)],
        [obj],
        [SpotRow("B", "floor", 56, 72)],
        {("b", "floor"): frozenset({(56, 72)})},
    )


def test_assembly_translates_regions_objects_spots_and_both_warp_ends(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = _data(tmp_path, monkeypatch)
    assemble_floors(data, tmp_path, "platinum")
    assert [(m.parent, m.x, m.level_count) for m in data.maps[:2]] == [("FLOOR_1F", 0, 0), ("FLOOR_1F", 512, 0)]
    assert (data.maps[-1].width, data.maps[-1].level_count) == (768, 3)
    assert (data.objects[0].x, data.spots[0].x) == (520, 568)
    assert (data.warps[0].target_x, data.warps[1].x, data.warps[1].target_x) == (536, 536, 8)
    assert data.terrain == {("b", "floor"): frozenset({(568, 72)})}
    assert data.coordinate_offsets["b"] == (512, 0)
    with Image.open(tmp_path / "floor-1f/2/0_2.webp") as tile:
        assert tile.getpixel((0, 0)) == (0, 0, 255)


def test_overlapping_rooms_are_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data = _data(tmp_path, monkeypatch, overlap=True)
    with pytest.raises(ValueError, match="recouvre"):
        assemble_floors(data, tmp_path, "platinum")


def test_editorial_assemblies_have_unique_parts_and_consistent_floors() -> None:
    for family in ("platinum", "diamond-pearl"):
        parts = read_assemblies(family)
        assert parts
        assert len({part.source for part in parts}) == len(parts)
        definitions = {(part.plan, part.number) for part in parts}
        assert len({number for _, number in definitions}) == len(definitions)


def test_editor_round_trip_preserves_native_points() -> None:
    key = TerrainKey("platinum", "room", "floor")
    native = {key: frozenset({(24, 40)})}
    session = SpotSession(native, {("platinum", "room"): (512, 256)})
    assert session.points(key, frozenset()) == frozenset({(536, 296)})
    assert session.native_points() == native
    session.toggle(key, frozenset(), (552, 312), lambda _: False)
    assert session.native_points()[key] == frozenset({(24, 40), (40, 56)})

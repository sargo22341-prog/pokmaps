"""Décors embarqués fixes et reproduction depuis les seules tuiles épinglées d’Émeraude."""

from pathlib import Path

import pytest
from PIL import Image

from pokemaps_data.encounter_backgrounds import (
    TERRAINS,
    build_encounter_backgrounds,
    validate_encounter_backgrounds,
)


def test_every_habitat_has_a_ground_and_a_matching_lake(assets: Path) -> None:
    validate_encounter_backgrounds(assets)
    for terrain in TERRAINS:
        with Image.open(assets / "encounter_backgrounds" / f"{terrain.name}_ground.webp") as image:
            assert len(set(image.get_flattened_data())) > 1


def test_invalid_texture_names_the_asset(assets: Path, tmp_path: Path) -> None:
    folder = tmp_path / "encounter_backgrounds"
    folder.mkdir()
    Image.new("RGB", (1, 1)).save(folder / "grass_ground.webp", "WEBP")
    with pytest.raises(ValueError, match=r"grass_ground\.webp"):
        validate_encounter_backgrounds(tmp_path)


def test_lake_centers_have_no_internal_bank_and_caves_have_no_grass(assets: Path) -> None:
    folder = assets / "encounter_backgrounds"
    with Image.open(folder / "grass_ground.webp") as image:
        grass_colors = set(image.get_flattened_data())
    for terrain in TERRAINS:
        with Image.open(folder / f"{terrain.name}_lake.webp") as image:
            assert len(set(image.crop((16, 16, 32, 32)).get_flattened_data())) == 1
            if terrain.name in {"cave", "ice", "floor", "sand"}:
                assert not grass_colors.intersection(image.get_flattened_data())


def test_emerald_sources_reproduce_all_bundled_textures(assets: Path, tmp_path: Path, source_cache_ready: None) -> None:
    build_encounter_backgrounds(Path(__file__).resolve().parents[1] / ".cache", tmp_path)
    for terrain in TERRAINS:
        for kind in ("ground", "lake"):
            relative = Path("encounter_backgrounds") / f"{terrain.name}_{kind}.webp"
            assert (tmp_path / relative).read_bytes() == (assets / relative).read_bytes()

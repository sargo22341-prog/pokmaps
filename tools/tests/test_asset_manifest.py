"""Contrôles des ressources versionnées et échecs explicites, sans sources externes."""

import re
import shutil
from pathlib import Path

import pytest

from pokemaps_data.asset_manifest import MANIFEST, check_manifest, write_manifest
from pokemaps_data.builder import DatabaseBuilder
from pokemaps_data.sprites import build_sprites
from pokemaps_data.validate import validate

from .conftest import CACHE


def test_bundled_assets_are_complete(assets: Path) -> None:
    check_manifest(assets)


@pytest.mark.parametrize(
    "relative", ["database/pokedex.db", "sprites/pokemon/static/25.webp", "maps/crystal/johto/0/0_0.webp"]
)
def test_missing_asset_names_the_file(assets: Path, tmp_path: Path, relative: str) -> None:
    # L'inventaire suffit à détecter l'absence avant toute lecture de la base.
    shutil.copyfile(assets / MANIFEST, tmp_path / MANIFEST)
    lines = (tmp_path / MANIFEST).read_text("utf-8").splitlines()
    selected = next(line for line in lines if line.endswith(f"  {relative}"))
    (tmp_path / MANIFEST).write_text(selected + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match=re.escape(str(tmp_path / relative))):
        check_manifest(tmp_path)


def test_modified_asset_is_rejected(assets: Path, tmp_path: Path) -> None:
    relative = "sprites/pokemon/static/25.webp"
    selected = next(line for line in (assets / MANIFEST).read_text("utf-8").splitlines() if line.endswith(relative))
    (tmp_path / MANIFEST).write_text(selected + "\n", encoding="utf-8")
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_bytes(b"image modifiee")
    with pytest.raises(ValueError, match="Asset modifié"):
        check_manifest(tmp_path)


def test_manifest_generation_rejects_missing_database(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"pokedex\.db"):
        write_manifest(tmp_path)


def test_missing_manifest_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Inventaire des assets absent"):
        check_manifest(tmp_path)


def test_pipeline_reproduces_bundled_assets(builder: DatabaseBuilder, assets_root: Path, assets: Path) -> None:
    icons = build_sprites(builder, CACHE, assets_root / "sprites")
    builder.write(assets_root / "database/pokedex.db", icons)
    assert validate(assets_root / "database/pokedex.db") == []
    shutil.copytree(assets / "licenses", assets_root / "licenses")
    # Vérifie toutes les tuiles, y compris celles absentes car entièrement transparentes.
    shutil.copyfile(assets / MANIFEST, assets_root / MANIFEST)
    check_manifest(assets_root)

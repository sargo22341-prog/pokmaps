"""Rendu de blocs des deux sources DS épinglées, sans réseau."""

from pathlib import Path

import pytest
from PIL import Image

from pokemaps_data.games import DIAMOND_PEARL, PLATINUM
from pokemaps_data.maps_render_gen4 import BlockRender, Gen4Renderer
from pokemaps_data.pret_gen4 import Gen4PretRepo
from pokemaps_data.sources import pret_dir

CACHE = Path(__file__).resolve().parents[1] / ".cache"
pytestmark = pytest.mark.pipeline


@pytest.mark.parametrize("group", ["platinum", "diamond-pearl"])
def test_twinleaf_block_reproducible_and_webp_tiles_are_lossless(
    group: str, source_cache_ready: None, tmp_path: Path
) -> None:
    game = PLATINUM if group == "platinum" else DIAMOND_PEARL
    repo = Gen4PretRepo(pret_dir(CACHE, game.pret_repo), game.pret_versions)
    header = next(header for header in repo.headers.values() if header.location in ("TwinleafTown", "TWINLEAF_TOWN"))
    matrix = repo.matrices[0]
    assert matrix.headers is not None and matrix.altitudes is not None
    row, column = next(
        (row, column)
        for row, values in enumerate(matrix.headers)
        for column, value in enumerate(values)
        if value == header.index
    )
    request = BlockRender(matrix.blocks[row][column], header.area, 2456, matrix.altitudes[row][column])
    renderer = Gen4Renderer(repo)
    first = renderer.render_block(request)
    second = renderer.render_block(request)
    assert first.getbbox() is not None and first.tobytes() == second.tobytes()
    count = renderer.write_block(request, tmp_path)
    tiles = list(tmp_path.rglob("*.webp"))
    assert count == len(tiles) and count > 0
    reconstructed = Image.new("RGBA", first.size)
    for path in tmp_path.joinpath("2").glob("*.webp"):
        y, x = (int(value) for value in path.stem.split("_"))
        with Image.open(path) as tile:
            assert tile.size == (256, 256)
            reconstructed.paste(tile, (x * 256, y * 256))
    assert reconstructed.tobytes() == first.tobytes()

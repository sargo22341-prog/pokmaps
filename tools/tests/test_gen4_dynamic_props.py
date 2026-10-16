"""Décors chargés par les moteurs en dehors des blocs statiques."""

import re
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from pokemaps_data.games import GEN4_GAMES
from pokemaps_data.maps_dynamic_gen4 import DynamicProps, prop_rotation
from pokemaps_data.maps_render_gen4 import BlockRender, Gen4Renderer
from pokemaps_data.pret_gen4 import Gen4PretRepo
from pokemaps_data.sources import pret_dir

CACHE = Path(__file__).resolve().parents[1] / ".cache"
pytestmark = pytest.mark.pipeline


def _repositories() -> tuple[Gen4PretRepo, ...]:
    return tuple(Gen4PretRepo(pret_dir(CACHE, game.pret_repo), game.pret_versions) for game in GEN4_GAMES)


def test_common_gym_and_transport_positions_are_proven_equal(source_cache_ready: None) -> None:
    platinum, diamond = _repositories()
    common = {35, 122, 154, 155, 156, 293, 509}
    results = []
    for repo in (platinum, diamond):
        props = DynamicProps(repo)
        assert props.by_block
        results.append([(p.header, p.model, p.position, p.rotation) for p in props.placements if p.header in common])
    assert results[0] == results[1]
    assert len(results[0]) == 52
    dp = Counter(p.header for p in DynamicProps(diamond).placements)
    assert dp[133] == 12 and dp[88] == dp[91] == 1
    assert Counter(p.header for p in DynamicProps(platinum).placements)[67] == 2


def test_floor_ceiling_excludes_upper_props_instead_of_their_underside(
    source_cache_ready: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repositories()[0]
    renderer = Gen4Renderer(repo)
    observed = []

    def record(file: object, *_args: object) -> tuple:
        observed.append(file)
        return ()

    monkeypatch.setattr(renderer, "_file", record)
    renderer.prepare_block(BlockRender(225, 24, 3426, ceiling=160 * 4096 - 1))
    assert not any(file is renderer._prop(300) for file in observed)
    observed.clear()
    renderer.prepare_block(BlockRender(225, 24, 3426, ceiling=320 * 4096 - 1))
    assert any(file is renderer._prop(300) for file in observed)
    assert not any(file is renderer._prop(301) for file in observed)


def test_clock_rotation_coefficients_match_nitro_fixed_point_table(source_cache_ready: None) -> None:
    repo = _repositories()[1]
    text = (repo.root / "arm9/lib/NitroSDK/src/FX_sincos.c").read_text(encoding="utf-8")
    values = re.findall(r"FX16_CONST\(([^)]+)\)", text)
    for angle in (0, 16384, 32768, 49152, 60049, 54595):
        index = (angle >> 4) * 2
        sine, cosine = (
            int((Decimal(v) * 4096).quantize(Decimal(1), rounding=ROUND_HALF_UP)) for v in values[index : index + 2]
        )
        transform = prop_rotation((0, angle, 0))
        assert transform.point((4096, 0, 0)) == (cosine, 0, -sine)

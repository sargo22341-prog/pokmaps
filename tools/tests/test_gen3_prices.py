"""Prix JSON des remakes : montants validés et alias des CT conservés."""

import json
from pathlib import Path

import pytest

from pokemaps_data.games import FIRERED_LEAFGREEN
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_gen3_prices import _price_rows
from pokemaps_data.sources import pret_dir

from .conftest import CACHE


def _repo(tmp_path: Path, items: object) -> Gen3PretRepo:
    folder = tmp_path / "src/data"
    folder.mkdir(parents=True)
    (folder / "items.json").write_text(json.dumps({"items": items}), encoding="utf-8")
    return Gen3PretRepo(tmp_path, FIRERED_LEAFGREEN.pret_versions)


def test_remake_json_prices_exclude_empty_slot(tmp_path: Path) -> None:
    repo = _repo(tmp_path, [{"itemId": "ITEM_NONE", "price": 0}, {"itemId": "ITEM_ULTRA_BALL", "price": 1200}])
    assert _price_rows(repo) == [("ITEM_ULTRA_BALL", 1200)]


@pytest.mark.parametrize("price", [True, "1200", -1, 65536, None])
def test_remake_invalid_json_price_is_rejected(tmp_path: Path, price: object) -> None:
    with pytest.raises(ValueError, match="prix d’objet invalide"):
        _price_rows(_repo(tmp_path, [{"itemId": "ITEM_ULTRA_BALL", "price": price}]))


def test_remake_pinned_prices_resolve_machine_aliases(source_cache_ready: None) -> None:
    repo = Gen3PretRepo(pret_dir(CACHE, FIRERED_LEAFGREEN.pret_repo), FIRERED_LEAFGREEN.pret_versions)
    assert "ITEM_NONE" not in repo.prices
    assert repo.prices["ITEM_ULTRA_BALL"] == 1200
    assert repo.prices["ITEM_TM10_HIDDEN_POWER"] == repo.prices["ITEM_TM10"] == 3000

"""Catalogue Hoenn distribué et lecture des variantes pret épinglées."""

import json
from pathlib import Path

import pytest

from pokemaps_data.hoenn_catalog import validate_hoenn_catalog
from pokemaps_data.pret_hoenn_content import berries, decorations
from pokemaps_data.pret_hoenn_contests import contest_effects, contest_moves
from pokemaps_data.sources import pret_dir


def test_distributed_catalog(assets: Path) -> None:
    validate_hoenn_catalog(assets)
    catalog = json.loads((assets / "hoenn.json").read_text(encoding="utf-8"))
    for group in catalog["groups"].values():
        oran = next(row for row in group["berries"] if row["identifier"] == "oran-berry")
        assert oran["stage_hours"] == 3
        assert oran["flavors"] == [10, 10, 10, 10, 10]
        assert (oran["min_yield"], oran["max_yield"], oran["smoothness"]) == (2, 3, 20)
        pound = next(row for row in group["moves"] if row["id"] == 1)
        assert (pound["category"], pound["appeal"], pound["jam"]) == ("TOUGH", 4, 0)
        stomp = next(row for row in group["moves"] if row["id"] == 23)
        assert stomp["previous"] == ["Groz’Yeux"]
        assert len(group["decorations"]) == 120
        assert next(row for row in group["decorations"] if row["identifier"] == "DECOR_SMALL_DESK")["price"] == 3000


def test_decoration_currencies_and_locations(assets: Path) -> None:
    data = json.loads((assets / "hoenn.json").read_text(encoding="utf-8"))["groups"]
    for group in data.values():
        casino = [
            row
            for row in group["sources"]
            if row["map"] == "mauville-city-game-corner" and row["kind"] == "sale_decoration"
        ]
        assert len(casino) in {3, 6}
        assert all(row["currency"] == "coins" and row["price"] == 1000 for row in casino)
        glass = [row for row in group["sources"] if row["map"] == "route113-glass-workshop"]
        assert glass and all(row["currency"] == "ashes" for row in glass)
        assert any("fortree" in row["map"] for row in group["sources"])
        assert any("department-store" in row["map"] for row in group["sources"])
    frontier = [row for row in data["emerald"]["sources"] if row["map"] == "battle-frontier-exchange-service-corner"]
    assert frontier and all(row["currency"] == "battle_points" for row in frontier)
    assert not any("frontier" in row["map"] for row in data["ruby-sapphire"]["sources"])


@pytest.mark.parametrize("key", ["berries", "moves", "decorations"])
def test_repeated_rows_are_rejected(assets: Path, tmp_path: Path, key: str) -> None:
    catalog = json.loads((assets / "hoenn.json").read_text(encoding="utf-8"))
    rows = catalog["groups"]["emerald"][key]
    rows[-1] = rows[0]
    (tmp_path / "hoenn.json").write_text(json.dumps(catalog), encoding="utf-8")
    with pytest.raises(ValueError, match=key):
        validate_hoenn_catalog(tmp_path)


@pytest.mark.parametrize("repo", ["pokeruby", "pokeemerald"])
def test_source_berry_and_decoration_tables(source_cache_ready: None, repo: str) -> None:
    root = pret_dir(Path(__file__).resolve().parents[1] / ".cache", repo)
    assert len(berries(root)) == 43
    cheri = berries(root)[0]
    assert cheri.identifier == "cheri-berry"
    assert cheri.flavors == (10, 0, 0, 0, 0)
    assert (cheri.stage_hours, cheri.min_yield, cheri.max_yield) == (3, 2, 3)
    furniture = decorations(root)
    assert len(furniture) == 120
    assert furniture[0].shape == "DECORSHAPE_1x1"
    assert furniture[0].price == 3000


@pytest.mark.parametrize("repo", ["pokeruby", "pokeemerald"])
def test_source_contests_and_combinations(source_cache_ready: None, repo: str) -> None:
    root = pret_dir(Path(__file__).resolve().parents[1] / ".cache", repo)
    moves = {row.move: row for row in contest_moves(root)}
    assert moves["STOMP"].previous == ("LEER",)
    assert moves["FIRE_PUNCH"].previous == ("SUNNY_DAY", "THUNDER_PUNCH", "ICE_PUNCH")
    assert moves["FIRE_PUNCH"].category == "CONTEST_CATEGORY_BEAUTY"
    effects = contest_effects(root)
    assert effects["CONTEST_EFFECT_HIGHLY_APPEALING"] == (4, 0)
    assert effects["CONTEST_EFFECT_GREAT_APPEAL_BUT_NO_MORE_MOVES"] == (8, 0)

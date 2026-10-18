"""Les cartes événementielles DS gardent leur provenance sans dépendre du texte français."""

import pytest

from pokemaps_data.external_events import event_map


@pytest.mark.parametrize(
    "identifier, key, entrance",
    [
        ("header-newmoon-island", "newmoon-island", True),
        ("header-newmoon-island-forest", "newmoon-island", False),
        ("newmoon-island-exterior", "newmoon-island", True),
        ("newmoon-island-interior", "newmoon-island", False),
        ("header-flower-paradise", "flower-paradise", True),
        ("flower-paradise", "flower-paradise", True),
        ("header-hall-of-origin", "hall-of-origin", True),
        ("hall-of-origin", "hall-of-origin", True),
    ],
)
def test_sinnoh_external_maps(identifier: str, key: str, entrance: bool) -> None:
    actual_key, order = event_map(identifier)
    assert actual_key == key
    assert (order > 0) == entrance


def test_regular_sinnoh_map_is_not_an_external_event() -> None:
    assert event_map("header-fullmoon-island") == (None, 0)

"""Exclusions par provenance, indépendantes de la disponibilité globale d'une espèce."""

import hashlib
import json
from pathlib import Path

import pytest

from pokemaps_data.obtainings_hgss import script_obtentions
from pokemaps_data.validate_special_hgss import validate_obtainings, validate_special_wild


def test_versioned_special_catalog_is_valid_without_source_cache() -> None:
    folder = Path(__file__).resolve().parents[2] / "docs/generations"
    data = (folder / "rencontres-hgss-particulieres.json").read_bytes()
    proof = json.loads((folder / "rencontres-hgss-preuve.json").read_text(encoding="utf-8"))
    assert hashlib.sha256(data).hexdigest() == proof["special_catalog_sha256"]
    catalog = json.loads(data)
    validate_special_wild(catalog["special_wild"])
    validate_obtainings(catalog["obtainings"])
    assert catalog["versions"] == ["heartgold", "soulsilver"]


def _root(folder: Path) -> Path:
    constants = folder / "include/constants"
    constants.mkdir(parents=True)
    (constants / "species.h").write_text("#define SPECIES_LATIAS 380\n#define SPECIES_RAYQUAZA 384\n", encoding="utf-8")
    scripts = folder / "files/fielddata/script/scr_seq"
    scripts.mkdir(parents=True)
    return scripts


def test_event_and_transfer_provenances_are_excluded_without_excluding_local_species(tmp_path: Path) -> None:
    scripts = _root(tmp_path)
    for name, content in (
        ("scr_seq_0750_T03.s", "entry:\n\tWildBattle SPECIES_LATIAS, 40, 0\n"),
        ("scr_seq_0776_T06.s", "entry:\n\tCreateRoamer 2\n"),
        ("scr_seq_0135_D52R0103.s", "entry:\n\tWildBattle SPECIES_RAYQUAZA, 50, 0\n"),
        ("scr_seq_0092_D36R0101.s", "entry:\n\tGiveSpikyEarPichu\n"),
    ):
        (scripts / name).write_text(content, encoding="utf-8")
    rows = script_obtentions(tmp_path)
    local = next(r for r in rows if r["kind"] == "roamer")
    assert local["species"] == [380] and local["ordinary_objective"] is True
    event = next(r for r in rows if r["native_location"] == "T03")
    assert event["species"] == [380] and event["ordinary_objective"] is False
    assert event["access"] == "external_event" and event["line"] == 2
    transfer = next(r for r in rows if r["native_location"] == "D52R0103")
    assert transfer["ordinary_objective"] is False and transfer["access"] == "external_transfer"
    assert all(r["exclusion_fr"] for r in rows if r is not local)


def test_unknown_variable_acquisition_fails_instead_of_becoming_empty(tmp_path: Path) -> None:
    scripts = _root(tmp_path)
    (scripts / "scr_seq_0001_TEST.s").write_text("entry:\n\tGiveMon VAR_TEMP_x4000, 5\n", encoding="utf-8")
    with pytest.raises(ValueError, match="candidats"):
        script_obtentions(tmp_path)


def test_exclusion_validator_rejects_an_external_source_counted_as_ordinary() -> None:
    row = {
        "id": "x",
        "source": "files/fielddata/script/scr_seq/x.s",
        "line": 1,
        "species": [172],
        "access": "external_event",
        "ordinary_objective": True,
        "exclusion_fr": "Distribution",
    }
    with pytest.raises(ValueError, match="exclusion"):
        validate_obtainings({"scripts": [row]})

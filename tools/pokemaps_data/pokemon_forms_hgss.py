"""Profils des formes HGSS et réutilisation vérifiée des sprites Noir/Blanc distribués."""

import csv
import hashlib
import re
import shutil
from pathlib import Path

from PIL import Image

from .form_sprites import UNOWN, FormSprites, validate_form_sprites
from .pret_hgss_pokemon import HgssPokemon, validate_personal
from .sources import DATA_DIR

_FORM_PROFILES = {
    "deoxys-attack": "DEOXYS_ATK",
    "deoxys-defense": "DEOXYS_DEF",
    "deoxys-speed": "DEOXYS_SPD",
    "wormadam-sandy": "WORMADAM_SANDY",
    "wormadam-trash": "WORMADAM_TRASH",
    "giratina-origin": "GIRATINA_ORIGIN",
    "shaymin-sky": "SHAYMIN_SKY",
    "rotom-heat": "ROTOM_HEAT",
    "rotom-wash": "ROTOM_WASH",
    "rotom-frost": "ROTOM_FROST",
    "rotom-fan": "ROTOM_FAN",
    "rotom-mow": "ROTOM_MOW",
}


def build_forms(data: HgssPokemon, rules: dict) -> list[dict]:
    profiles = {row["species"]: (i, row) for i, row in enumerate(data.personal)}
    if set(profiles) != {row["species"] for row in data.personal} or len(profiles) != 508:
        raise ValueError("HGSS : profils de formes répétés")
    result = []
    tutors = {row["mon"].removeprefix("SPECIES_"): row["moves"] for row in data.tutors}
    with (DATA_DIR / "hgss_pokemon_forms.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 47 or len({row["identifier"] for row in rows}) != 47:
        raise ValueError("HGSS : catalogue de 47 formes attendu")
    for row in rows:
        species = int(row["pokemon_id"])
        if not 1 <= species <= 493 or not row["name_fr"].strip():
            raise ValueError(f"HGSS : espèce ou nom de forme invalide : {row}")
        if any(
            re.fullmatch(r"[a-z0-9-]+", row[key]) is None
            for key in ("identifier", "sprite_folder", "sprite_identifier")
        ):
            raise ValueError(f"HGSS : identifiant ou chemin de sprite invalide : {row}")
        profile_id, profile = (
            profiles[_FORM_PROFILES[row["identifier"]]]
            if row["identifier"] in _FORM_PROFILES
            else (species, data.personal[species])
        )
        validate_personal(profile, row["identifier"])
        for version in rules["versions"]:
            result.append(
                dict(
                    row,
                    version=version,
                    personal_member=profile_id,
                    personal=profile,
                    level_moves=data.level_moves[profile_id],
                    tutor_moves=tutors[profile["species"]],
                    type_rule_fr=_type_rule(species, row["identifier"]),
                )
            )
    return result


def _type_rule(species: int, identifier: str) -> str:
    if species == 493:
        return f"Multitype et Plaque tenue : {identifier.removeprefix('arceus-')}. Aucun type Fée en HGSS."
    if species == 351:
        return "Météo adapte le type à la météo du combat ; les données personnelles restent celles de Morphéo."
    return "Types des données personnelles HGSS ; les appareils de Motisma restent Électrik/Spectre."


def copy_sprites(assets: Path, root: Path, staging: Path, forms: list[dict]) -> dict[str, str]:
    entries = dict(line.split("  ", 1)[::-1] for line in (assets / "assets.sha256").read_text("utf-8").splitlines())
    required = {("pokemon", str(i)) for i in range(1, 494)}
    required |= {(row["sprite_folder"], row["sprite_identifier"]) for row in forms}
    required |= {(UNOWN.folder, form) for form in UNOWN.forms}
    hashes = {}
    for folder, identifier in sorted(required):
        for style in ("", "shiny/"):
            for motion in ("static", "animated"):
                relative = f"sprites/{folder}/{style}{motion}/{identifier}.webp"
                source = assets / relative
                digest = hashlib.sha256(source.read_bytes()).hexdigest()
                if entries.get(relative) != digest:
                    raise ValueError(f"HGSS : sprite distribué absent de l'inventaire ou modifié : {relative}")
                destination = staging / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
                hashes[relative] = digest
    groups: dict[str, set[str]] = {}
    for folder, identifier in required:
        groups.setdefault(folder, set()).add(identifier)
    for folder, identifiers in groups.items():
        validate_form_sprites(staging / "sprites", FormSprites(0, folder, tuple(sorted(identifiers))))
    source = root / "files/poketool/pokegra/otherpoke/pichu/spiky/front.png"
    with Image.open(source) as image:
        if image.size != (160, 80):
            raise ValueError("HGSS : planche native de Pichu Troizépi inattendue")
    destination = staging / "sprites/pichu-spiky-hgss.png"
    shutil.copyfile(source, destination)
    hashes[destination.relative_to(staging).as_posix()] = hashlib.sha256(source.read_bytes()).hexdigest()
    return hashes

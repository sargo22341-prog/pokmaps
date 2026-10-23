"""Aperçu validé des personnages HGSS, conservé séparément des jeux distribués."""

import hashlib
import json
import textwrap
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageDraw

from .catalog_characters_hgss import character_catalog
from .maps_render_hgss import HgssRenderer
from .placements_characters_hgss import place_characters
from .pret_hgss_maps import HgssMapRepo
from .preview_placement_hgss import check_placement, digest
from .preview_pokemon_hgss import _replace_preview
from .review_characters_hgss import write_character_review
from .sources import HGSS_PRET_COMMIT
from .sources_characters_hgss import CONTRACT
from .sprites_hgss import actor_frame
from .validate_characters_hgss import validate_character_catalog


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_characters(cache: Path, output: Path) -> None:
    check_placement(output / "hgss-placement")
    root = cache / "hgss-qualification"
    catalog = character_catalog(root)
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".hgss-characters-", dir=output) as temporary:
        staging = Path(temporary) / "staging"
        staging.mkdir()
        catalog["prerequisites"] = {
            name: digest(output / name) for name in ("hgss-maps/inventory.json", "hgss-placement/inventory.json")
        }
        catalog["recipe"] = recipe()
        catalog["sprites"] = export_sprites(root, staging, catalog["actors"])
        catalog["placements"] = place_characters(root, output / "hgss-maps/atlas", staging, catalog["actors"])
        validate_character_catalog(catalog)
        write_character_review(staging, catalog)
        write_json(staging / "characters.json", catalog)
        write_json(
            staging / "inventory.json",
            {p.relative_to(staging).as_posix(): _asset_digest(p) for p in sorted(staging.rglob("*")) if p.is_file()},
        )
        check_characters(staging, output)
        _replace_preview(staging, output / "hgss-characters", Path(temporary) / "previous")
    print(
        f"HGSS : {len(catalog['actors'])} acteurs, {len(catalog['trainers'])} équipes, "
        f"{len(catalog['service_steps'])} offres résolues et {len(catalog['field_items'])} objets placés"
    )


def recipe() -> dict[str, str]:
    names = (
        "preview_characters_hgss.py",
        "character_actors_hgss.py",
        "pret_hgss_trainers.py",
        "pret_hgss_rematches.py",
        "pret_hgss_scripts.py",
        "pret_hgss_field_items.py",
        "pret_hgss_services.py",
        "sources_characters_hgss.py",
        "obtainings_hgss.py",
        "validate_characters_hgss.py",
        "catalog_maps_hgss.py",
        "maps_render_hgss.py",
        "maps_sprites_gen4.py",
        "pret_hgss_maps.py",
        "pret_hgss_binary.py",
        "pret_hgss_pokemon.py",
        "pret_gen4_source.py",
        "pret_gen4_textures.py",
        "preview_placement_hgss.py",
        "catalog_characters_hgss.py",
        "calendar_hgss.py",
        "character_battles_hgss.py",
        "character_curation_hgss.py",
        "conditions_hgss.py",
        "names_hgss.py",
        "offer_rules_hgss.py",
        "placements_characters_hgss.py",
        "pret_hgss_battles.py",
        "pret_hgss_flow.py",
        "pret_hgss_flow_context.py",
        "pret_hgss_offer_effects.py",
        "pret_hgss_offers.py",
        "services_characters_hgss.py",
        "shops_hgss.py",
        "sprites_hgss.py",
        "pret_gen4_flow.py",
        "pret_gen4_flow_values.py",
        "pret_gen4_flow_chains.py",
        "maps_review_gen4.py",
        "review_characters_hgss.py",
        "presence_characters_hgss.py",
        "catalog_pokemon_hgss.py",
        "pokeapi.py",
        "pret_gen4_land.py",
    )
    result = {name: digest(Path(__file__).with_name(name)) for name in names}
    data = Path(__file__).resolve().parents[1] / "data"
    result.update({f"data/{path.name}": digest(path) for path in sorted(data.glob("hgss_*csv"))})
    return result


def check_characters(folder: Path, prerequisites: Path | None = None) -> dict:
    from .placement_hgss import read_placement_json

    inventory = read_placement_json(folder / "inventory.json")
    actual = {
        p.relative_to(folder).as_posix(): _asset_digest(p)
        for p in folder.rglob("*")
        if p.is_file() and p.name != "inventory.json"
    }
    if inventory != actual:
        raise ValueError("HGSS : inventaire des personnages modifié")
    data = read_placement_json(folder / "characters.json")
    if data["commit"] != HGSS_PRET_COMMIT or data["recipe"] != recipe():
        raise ValueError("HGSS : provenance ou recette des personnages périmée")
    if data["native_sources"] != read_placement_json(CONTRACT):
        raise ValueError("HGSS : contrat des personnages périmé")
    base = prerequisites or folder.parent
    for name, expected in data["prerequisites"].items():
        if digest(base / name) != expected:
            raise ValueError(f"HGSS : prérequis de personnages périmé : {name}")
    validate_character_catalog(data)
    return data


def _asset_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export_sprites(root: Path, folder: Path, actors: list[dict]) -> list[dict]:
    renderer = HgssRenderer(HgssMapRepo(root, "heartgold"))
    names = sorted({row["native"]["sprite"] for row in actors if row["useful"]})
    if len(names) > 512:
        raise ValueError("HGSS : plus de 512 sprites de personnages")
    target = folder / "sprites"
    target.mkdir()
    rows = []
    sheet = Image.new("RGB", (960, ((len(names) + 7) // 8) * 144), "#ededed")
    draw = ImageDraw.Draw(sheet)
    for index, name in enumerate(names):
        x, y = index % 8 * 120, index // 8 * 144
        label = name.removeprefix("SPRITE_").replace("_", " ")
        draw.multiline_text((x + 2, y + 88), "\n".join(textwrap.wrap(label, 18)), fill="black")
        frame, metadata = actor_frame(renderer, name)
        path = target / f"{name}.png"
        frame.save(path)
        sheet.paste(frame, (x + (120 - frame.width) // 2, y + 84 - frame.height), frame)
        rows.append(dict(sprite=name, **metadata, image=path.relative_to(folder).as_posix(), status="decoded"))
    sheet.save(folder / "sprites-review.png")
    return rows

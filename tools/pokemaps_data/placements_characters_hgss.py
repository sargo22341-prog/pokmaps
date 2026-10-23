"""Projection des acteurs sur l'atlas HGSS et planches de contrôle par lieu."""

import json
from pathlib import Path

from PIL import Image, ImageDraw

from .character_curation_hgss import editorial_rows
from .maps_render_hgss import camera_cotangent
from .maps_review_gen4 import _review_font
from .pret_gen4_land import FX_ONE, heights
from .pret_hgss_maps import HgssMapRepo
from .pret_hgss_scripts import read_scripts


def place_characters(root: Path, atlas: Path, folder: Path, actors: list[dict]) -> dict:
    catalog = json.loads((atlas / "catalog.json").read_text(encoding="utf-8"))
    maps = {row["header"]: row for row in catalog["maps"]}
    repo = HgssMapRepo(root, "heartgold")
    scripts = read_scripts(root)
    useful = [actor for actor in actors if actor["useful"] and not actor["alias_of"]]
    _scene_positions(useful)
    for header in sorted({a["header"] for a in useful}):
        record = maps[header]
        native = repo.headers[header]
        blocks = {(x, z): (repo.land(block), altitude) for x, z, block, altitude in repo.blocks(native)}
        cotangent = camera_cotangent(root, native)
        for actor in (a for a in useful if a["header"] == header):
            actor["script_positions"] = [
                dict(
                    x=int(s.arguments[1], 0),
                    y=int(s.arguments[2], 0),
                    z=int(s.arguments[3], 0),
                    source=scripts[actor["bank"]].source,
                    line=s.line,
                )
                for s in scripts[actor["bank"]].steps
                if s.command == "MovePersonFacing"
                and s.arguments[0] == actor["native"]["identity"]
                and all(v.lstrip("-").isdigit() for v in s.arguments[1:4])
            ]
            _project_actor(actor, blocks, cotangent, record)
    pages = _review_pages(atlas, folder, useful, maps)
    return dict(
        count=len(useful),
        pages=pages,
        projection="BDHC nearest native event height; native height if absent",
        native_height_only=sum(a["placement"]["height_source"] == "event" for a in useful),
    )


def _project_actor(actor: dict, blocks: dict, cotangent: int, record: dict) -> None:
    native = actor["native"]
    x, z, y = native["x"], native["z"], native["y"]
    if "scene_placement" in actor:
        x, z = int(actor["scene_placement"]["x"]), int(actor["scene_placement"]["z"])
    elif (x // 32, z // 32) not in blocks or block_surface_missing(blocks, x, z):
        positions = actor["script_positions"]
        if positions:
            x, z = positions[0]["x"], positions[0]["z"]
    block = blocks.get((x // 32, z // 32))
    surface = ()
    if block is not None and block[0].bdhc is not None:
        surface = tuple(
            height + block[1] * 8 * FX_ONE
            for height in heights(block[0].bdhc, (x % 32 * 16 - 248) * FX_ONE, (z % 32 * 16 - 248) * FX_ONE)
        )
    height = min(surface, key=lambda value: abs(value - y)) if surface else y
    if actor.get("scene_placement", {}).get("surface") == "upper":
        if not surface:
            raise ValueError(f"HGSS : pont de scène sans surface BDHC : {native['identity']}")
        height = max(surface)
    origin = record["origin_pixels"]
    point = [x * 16 + 8 - origin[0], z * 16 + 8 - height * cotangent // FX_ONE // FX_ONE - origin[1]]
    display = [value + delta for value, delta in zip(point, actor["display_offset"], strict=True)]
    inside = 0 <= display[0] < record["size"][0] and 0 <= display[1] < record["size"][1]
    actor["placement"] = dict(
        point=point,
        display=display,
        height_fx32=height,
        height_source="BDHC" if surface else "event",
        inside=inside,
        map=record["image"],
        visibility=native["flag"],
    )
    actor["placement"]["tile"] = [x, z]
    layers = [layer for layer in record["layers"] if height < layer["ceiling_fx32"]]
    if surface and height < max(surface) and layers:
        layer = min(layers, key=lambda row: row["ceiling_fx32"])
        actor["placement"].update(map=layer["image"], layer_ceiling_fx32=layer["ceiling_fx32"])
    if not inside:
        raise ValueError(f"HGSS : personnage hors image : {actor['header']} {native['identity']} {display}")


def _scene_positions(actors: list[dict]) -> None:
    corrections = {(int(row["header"]), row["identity"]): row for row in editorial_rows("hgss_scene_placements.csv")}
    used = set()
    for actor in actors:
        key = actor["header"], actor["native"]["identity"]
        if key in corrections:
            actor["scene_placement"] = corrections[key]
            used.add(key)
    if used != set(corrections):
        raise ValueError("HGSS : placements de scène inutilisés")


def block_surface_missing(blocks: dict, x: int, z: int) -> bool:
    block = blocks.get((x // 32, z // 32))
    return block is not None and (
        block[0].bdhc is None or not heights(block[0].bdhc, (x % 32 * 16 - 248) * FX_ONE, (z % 32 * 16 - 248) * FX_ONE)
    )


def _review_pages(atlas: Path, folder: Path, actors: list[dict], maps: dict) -> list[str]:
    target = folder / "placements"
    target.mkdir()
    pages = []
    for start in range(0, len(actors), 20):
        sheet = Image.new("RGB", (1200, 1000), "#eeeeee")
        draw = ImageDraw.Draw(sheet)
        font = _review_font()
        for index, actor in enumerate(actors[start : start + 20]):
            actor["review_image"] = f"placements/{start // 20:03d}.png"
            x, y = index % 5 * 240, index // 5 * 250
            px, py = actor["placement"]["display"]
            with Image.open(atlas / actor["placement"]["map"]) as image:
                crop = image.convert("RGB").crop((px - 110, py - 160, px + 110, py + 40))
            sprite = folder / "sprites" / f"{actor['native']['sprite']}.png"
            with Image.open(sprite) as frame:
                crop.paste(frame, (110 - frame.width // 2, 160 - frame.height), frame)
            ImageDraw.Draw(crop).ellipse((106, 156, 114, 164), fill="red", outline="white", width=1)
            sheet.paste(crop, (x + 10, y + 5))
            draw.text(
                (x + 5, y + 208), f"{actor['header']}:{actor['event']} {actor['name_fr'][:27]}", fill="black", font=font
            )
            draw.text((x + 5, y + 225), actor["place_fr"][:30], fill="black", font=font)
        name = f"placements/{start // 20:03d}.png"
        sheet.save(folder / name)
        pages.append(name)
    return pages

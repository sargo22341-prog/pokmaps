"""Personnages HGSS, équipes, revanches et objets dans le modèle commun des cartes."""

from pathlib import Path

from PIL import Image

from .maps_characters import ObjectRow
from .maps_layout import identifier
from .maps_render_hgss import camera_cotangent
from .pokeapi import PokeApi
from .pret_gen4_land import FX_ONE, heights
from .pret_hgss_maps import HgssMapRepo
from .pret_models import VariantKind
from .references_hgss import HgssReferences
from .sources import PREVIEW_DIR, fetch_pokeapi_csv


def character_rows(root: Path, catalog: dict, maps: dict, offsets: dict, output: Path) -> list[ObjectRow]:
    api = PokeApi(fetch_pokeapi_csv(root.parent))
    refs = HgssReferences(root, api)
    repo = HgssMapRepo(root, "heartgold")
    result = []
    for actor in catalog["actors"]:
        if not actor["useful"] or actor["alias_of"]:
            continue
        const = maps[actor["header"]]["const"]
        dx, dy = offsets[identifier(const)]
        x, y = actor["placement"]["display"]
        if "layer_ceiling_fx32" in actor["placement"]:
            from .layers_application_hgss import actor_layer

            const = actor_layer(maps[actor["header"]], actor["placement"]["layer_ceiling_fx32"])
        sprite = actor["native"]["sprite"]
        row = ObjectRow(
            const,
            "npc",
            x + dx,
            y + dy,
            sprite,
            None,
            None,
            None,
            None,
            key=f"hgss:{actor['header']}:{actor['event']}",
            name_fr=actor["name_fr"],
            source_cell=tuple(actor["placement"]["tile"]),
        )
        _teams(row, actor, catalog, refs)
        if row.kind == "npc":
            row.appearance = "npc"
        from .maps_offers_hgss import actor_offers

        row.offers = actor_offers(actor, catalog, refs)
        _sprite(sprite, output)
        result.append(row)
    result.extend(_field_items(repo, catalog, maps, offsets, refs))
    from .maps_fixed_hgss import fixed_rows

    result.extend(fixed_rows(root, catalog, maps, offsets, api, refs))
    return result


def _field_items(repo: HgssMapRepo, catalog: dict, maps: dict, offsets: dict, refs: HgssReferences) -> list[ObjectRow]:
    from .layers_application_hgss import surface_map

    result = []
    for entry in catalog["field_items"]:
        record = _item_map(repo, maps, entry)
        const = record["const"]
        x, y = project(repo, record, entry["native"])
        dx, dy = offsets[identifier(const)]
        item = entry["item"]
        name = refs.item(item["item"])
        text = catalog["names"]["items"][str(item["item"])]
        if item["quantity"] != 1:
            text += f" ×{item['quantity']}"
        result.append(
            ObjectRow(
                surface_map(record, surface_height(repo, record, entry["native"])),
                "hidden_item" if item["kind"] == "hidden" else "item",
                x + dx,
                y + dy,
                None,
                name,
                None,
                None,
                None,
                name_fr=text,
            )
        )
    return result


def _item_map(repo: HgssMapRepo, maps: dict, entry: dict) -> dict:
    record = maps[entry["header"]]
    cell = entry["native"]["x"] // 32, entry["native"]["z"] // 32
    header = repo.headers[record["header"]]
    if cell in {(a, b) for a, b, _, _ in repo.blocks(header)}:
        return record
    candidates = [
        r
        for r in maps.values()
        if repo.headers[r["header"]].matrix == header.matrix
        and cell in {(a, b) for a, b, _, _ in repo.blocks(repo.headers[r["header"]])}
    ]
    if not candidates:
        raise ValueError(f"HGSS : objet sans carte native : {entry}")
    return min(candidates, key=lambda r: r["header"])


def project(repo: HgssMapRepo, record: dict, event: dict) -> tuple[int, int]:
    x, z = event["x"], event["z"]
    height = surface_height(repo, record, event)
    origin = record["origin_pixels"]
    return x * 16 + 8 - origin[0], z * 16 + 8 - height * camera_cotangent(
        repo.root, repo.headers[record["header"]]
    ) // FX_ONE // FX_ONE - origin[1]


def surface_height(repo: HgssMapRepo, record: dict, event: dict) -> int:
    x, z, y = event["x"], event["z"], event.get("y", 0)
    header = repo.headers[record["header"]]
    blocks = {(a, b): (n, altitude) for a, b, n, altitude in repo.blocks(header)}
    if (x // 32, z // 32) not in blocks:
        raise ValueError(f"HGSS : événement hors des blocs : {record['const']} {event}")
    number, altitude = blocks[x // 32, z // 32]
    block = repo.land(number)
    surfaces = (
        () if block.bdhc is None else heights(block.bdhc, (x % 32 * 16 - 248) * FX_ONE, (z % 32 * 16 - 248) * FX_ONE)
    )
    candidates = [h + altitude * 8 * FX_ONE for h in surfaces]
    return min(candidates, key=lambda h: abs(h - y)) if candidates else y


def _sprite(name: str, output: Path) -> None:
    path = output / "sprites" / f"{name}.webp"
    if path.is_file():
        return
    path.parent.mkdir(exist_ok=True)
    with Image.open(PREVIEW_DIR / "hgss-characters/sprites" / f"{name}.png") as image:
        image.save(path, "WEBP", lossless=True)


def _teams(row: ObjectRow, actor: dict, catalog: dict, refs: HgssReferences) -> None:
    trainers = {r["id"]: r for r in catalog["trainers"]}
    numbers = actor["trainers"]
    if not numbers:
        return
    row.kind = "trainer"
    row.trainer_class = trainers[numbers[0]]["trainer_class"]
    selected = {}
    for battle in catalog["resolved_battles"]:
        if not any(a["header"] == actor["header"] and a["event"] == actor["event"] for a in battle["actors"]):
            continue
        for variant in battle["variants"]:
            for number in variant["opponents"]:
                if number in numbers and variant["starter"]:
                    selected[number] = variant["starter"]
    if not selected and len(numbers) == 3:
        for number in numbers:
            starters = [p["species"] for p in trainers[number]["party"] if 152 <= p["species"] <= 160]
            if len(starters) == 1:
                base = 152 + (starters[0] - 152) // 3 * 3
                selected[number] = {152: 158, 155: 152, 158: 155}[base]
    if selected:
        for team, number in enumerate(numbers, 1):
            if number not in selected:
                raise ValueError(f"HGSS : équipe sans choix de départ : {actor['header']} {number}")
            row.variants.append(
                (VariantKind.PLAYER_STARTER, refs.species[selected[number]], _party(trainers[number], refs))
            )
            _held(row, trainers[number], refs, team)
    else:
        row.party = _party(trainers[numbers[0]], refs)
        extra = list(numbers[1:])
        for series in catalog["rematches"]["series"]:
            if series["base"] in numbers:
                extra += [n for n in series["teams"] if n and n not in numbers]
        _held(row, trainers[numbers[0]], refs, 1)
        for team, number in enumerate(dict.fromkeys(extra), 2):
            row.rematches.append(_party(trainers[number], refs))
            _held(row, trainers[number], refs, team)


def _party(trainer: dict, refs: HgssReferences) -> list[tuple[str, int, tuple[str, ...]]]:
    return [
        (refs.species[p["species"]], p["level"], tuple(refs.moves[m] for m in p["moves"] if m))
        for p in trainer["party"]
    ]


def _held(row: ObjectRow, trainer: dict, refs: HgssReferences, team: int) -> None:
    for slot, mon in enumerate(trainer["party"], 1):
        if mon["item"]:
            row.held_items[team, slot] = refs.item(mon["item"])

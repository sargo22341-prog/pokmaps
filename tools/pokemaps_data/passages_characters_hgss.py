"""Dégagement des portes HGSS sur des cases natives praticables et bornées."""

from pathlib import Path

from .maps import GameMapData
from .maps_characters_hgss import project
from .maps_layout import identifier
from .pret_hgss_maps import HgssMapRepo


def clear_passages(data: GameMapData, root: Path, maps: dict, offsets: dict) -> None:
    passages = {(w.map_const, w.x, w.y) for w in data.warps}
    repo = HgssMapRepo(root, "heartgold")
    by_const = {r["const"]: r for r in maps.values()}
    for row in data.objects:
        if row.source_cell is None or (row.map_const, row.x, row.y) not in passages:
            continue
        record = by_const.get(row.map_const) or maps[int(row.key.split(":")[1])]
        header = repo.headers[record["header"]]
        blocks = {(x, z): repo.land(n) for x, z, n, _ in repo.blocks(header)}
        forbidden = {(a.x, a.z) for a in repo.events(header).actors} | {(w.x, w.z) for w in repo.events(header).warps}
        dx, dy = offsets[identifier(record["const"])]
        candidates = []
        for radius in range(1, 4):
            for shift_x, shift_z in ((0, radius), (radius, 0), (-radius, 0), (0, -radius)):
                x, z = row.source_cell[0] + shift_x, row.source_cell[1] + shift_z
                block = blocks.get((x // 32, z // 32))
                if block is None or block.collision(x % 32, z % 32) or (x, z) in forbidden:
                    continue
                point = project(repo, record, dict(x=x, z=z))
                translated = point[0] + dx, point[1] + dy
                if (row.map_const, *translated) not in passages:
                    candidates.append(translated)
            if candidates:
                break
        if not candidates:
            raise ValueError(f"HGSS : aucun déplacement praticable autour du passage : {row.key}")
        row.x, row.y = candidates[0]

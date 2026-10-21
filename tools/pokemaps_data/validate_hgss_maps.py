"""Preuves bornées des sources, passages et surfaces du prototype HGSS."""

import hashlib
import json
import subprocess
from pathlib import Path

from .pret_gen4_land import FX_ONE, heights
from .pret_hgss_maps import PROOF_MAPS, HgssHeader, HgssMapRepo
from .sources import HGSS_PRET_COMMIT

_PROOF_INVENTORY = Path(__file__).resolve().parents[2] / "docs/generations/cartes-hgss-sources.json"


def _file_digest(path: Path) -> str:
    if path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError(f"{path} : ressource HGSS trop volumineuse")
    data = path.read_bytes()
    if path.suffix in {".h", ".c", ".s", ".txt", ".json"}:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def validate_sources(root: Path) -> dict[str, str]:
    inventory = json.loads(_PROOF_INVENTORY.read_text(encoding="utf-8"))
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
        stdin=subprocess.DEVNULL,
    )
    if result.stdout.strip() != HGSS_PRET_COMMIT or inventory["commit"] != HGSS_PRET_COMMIT:
        raise ValueError(f"{root} : commit HGSS différent du prototype épinglé")
    for relative, expected in inventory["files"].items():
        path = root / relative
        if not path.is_file() or _file_digest(path) != expected:
            raise ValueError(f"{relative} : source du prototype HGSS absente ou modifiée")
    return inventory["files"]


def surface_grid(repo: HgssMapRepo, header: HgssHeader) -> list[dict]:
    cells = []
    for column, row, index, altitude in repo.blocks(header):
        block = repo.land(index)
        if block.bdhc is None:
            raise ValueError(f"{header.constant} bloc {index} : surface BDHC indispensable absente")
        for z in range(32):
            for x in range(32):
                values = heights(block.bdhc, (x * 16 + 8 - 256) * FX_ONE, (z * 16 + 8 - 256) * FX_ONE)
                cells.append(
                    {
                        "x": column * 32 + x,
                        "z": row * 32 + z,
                        "attribute": block.attributes[z * 32 + x],
                        "heights": [value + altitude * 8 * FX_ONE for value in values],
                    }
                )
    return cells


def validate_proof(repo: HgssMapRepo) -> dict:
    selected = {h.constant: h for h in repo.headers.values() if h.constant.removeprefix("MAP_") in PROOF_MAPS}
    if len(selected) != len(PROOF_MAPS):
        raise ValueError("HGSS : lieux du prototype incomplets")
    for header in selected.values():
        repo.blocks(header)
        for warp in repo.events(header).warps:
            destination = repo.headers[warp.destination]
            targets = repo.events(destination).warps
            if warp.anchor >= len(targets):
                raise ValueError(f"{header.constant} : ancre {warp.anchor} absente dans {destination.constant}")
    links = _return_links(repo, selected)
    route = surface_grid(repo, selected["MAP_ROUTE_29"])
    town = surface_grid(repo, selected["MAP_NEW_BARK"])
    joined = _boundary(route, town)
    layers = [cell for cell in surface_grid(repo, selected["MAP_ROUTE_47"]) if len(cell["heights"]) > 1]
    if not joined or not layers:
        raise ValueError("HGSS : continuité Route 29 ou surfaces superposées non démontrées")
    return {"return_links": links, "route_29_boundary": joined, "overlapping_surfaces": layers}


def _return_links(repo: HgssMapRepo, selected: dict[str, HgssHeader]) -> list[dict]:
    town = selected["MAP_NEW_BARK"]
    warps = repo.events(town).warps
    links = []
    for name in ("MAP_NEW_BARK_ELMS_LAB_1F", "MAP_NEW_BARK_ELMS_LAB_2F"):
        interior = selected[name]
        entrances = [(i, warp) for i, warp in enumerate(warps) if warp.destination == interior.index]
        if len(entrances) != 1:
            raise ValueError(f"{name} : entrée HGSS absente ou ambiguë")
        index, entrance = entrances[0]
        returning = repo.events(interior).warps[entrance.anchor]
        if returning.destination != town.index or returning.anchor != index:
            raise ValueError(f"{name} : passage retour HGSS incohérent")
        links.append({"outside": town.index, "warp": index, "inside": interior.index, "anchor": entrance.anchor})
    return links


def _boundary(route: list[dict], town: list[dict]) -> list[list[int]]:
    lookup = {(cell["x"], cell["z"]): cell for cell in route}
    joined = []
    for cell in town:
        neighbor = lookup.get((cell["x"] - 1, cell["z"]))
        if neighbor is None or (cell["attribute"] | neighbor["attribute"]) & 0x8000:
            continue
        if set(cell["heights"]) & set(neighbor["heights"]):
            joined.append([neighbor["x"], cell["z"], cell["x"], cell["z"]])
    return joined

"""Inventaire éditorial HGSS, sélection des périmètres et références natives de navigation."""

import csv
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .pret_gen4_land import FX_ONE, heights
from .pret_hgss_maps import HgssMapRepo

_CATALOG = Path(__file__).resolve().parents[1] / "data/hgss_maps.csv"
_SCOPES = frozenset(("johto", "kanto", "special", "excluded"))
_FIELDS = ("header", "const", "scope", "name_fr", "plan", "floor", "reason")


@dataclass(frozen=True)
class HgssMapEntry:
    header: int
    const: str
    scope: str
    name_fr: str
    plan: str
    floor: str
    reason: str


def read_catalog(repo: HgssMapRepo, path: Path = _CATALOG) -> tuple[HgssMapEntry, ...]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(_FIELDS):
            raise ValueError(f"{path} : colonnes du catalogue HGSS invalides")
        entries = tuple(
            HgssMapEntry(int(row["header"]), *(row[key] for key in reader.fieldnames[1:])) for row in reader
        )
    if len(entries) != len(repo.headers) or {e.header for e in entries} != set(repo.headers):
        raise ValueError(f"{path} : inventaire HGSS incomplet ou dupliqué")
    for entry in entries:
        if entry.const != repo.headers[entry.header].constant or entry.scope not in _SCOPES:
            raise ValueError(f"{path} : identité ou périmètre invalide : {entry.const}")
        if entry.scope == "excluded":
            if not entry.reason or entry.plan or entry.name_fr or entry.floor:
                raise ValueError(f"{entry.const} : exclusion HGSS non justifiée ou plan hors périmètre")
            continue
        if (
            not entry.name_fr.strip()
            or not re.fullmatch(r"base|b?[1-9][0-9]?f", entry.floor)
            or not re.fullmatch(r"[a-z0-9_-]+", entry.plan)
        ):
            raise ValueError(f"{entry.const} : nom français, étage ou plan absent")
    plans = {entry.plan: entry.floor for entry in entries if entry.scope != "excluded"}
    if any(plans[entry.plan] != entry.floor for entry in entries if entry.scope != "excluded"):
        raise ValueError(f"{path} : un plan HGSS mélange plusieurs étages")
    return entries


def selected_entries(entries: tuple[HgssMapEntry, ...], scope: str) -> tuple[HgssMapEntry, ...]:
    if scope not in (_SCOPES - {"excluded"}) | {"atlas"}:
        raise ValueError(f"Périmètre du catalogue HGSS inconnu : {scope}")
    return tuple(e for e in entries if e.scope == scope or (scope == "atlas" and e.scope != "excluded"))


def passage_catalog(repo: HgssMapRepo, entries: tuple[HgssMapEntry, ...], scope: str = "johto") -> list[dict]:
    lookup = {entry.header: entry for entry in entries}
    result = []
    selected = selected_entries(entries, scope)
    retained = {entry.header for entry in selected}
    for entry in selected:
        for index, warp in enumerate(repo.events(repo.headers[entry.header]).warps):
            record = {"source": entry.header, "index": index, **asdict(warp)}
            if warp.destination == 4095:
                if warp.anchor != 256:
                    raise ValueError(f"{entry.const} : destination mémorisée inconnue : {warp.anchor}")
                record.update(kind="variable", target_scope="memory", target_name="Destination mémorisée")
            else:
                destination = lookup[warp.destination]
                targets = repo.events(repo.headers[warp.destination]).warps
                if warp.anchor >= len(targets):
                    raise ValueError(f"{entry.const} : ancre {warp.anchor} absente dans {destination.const}")
                record.update(
                    kind="fixed" if destination.header in retained else "boundary",
                    target_scope=destination.scope,
                    target_name=destination.name_fr or destination.const,
                    target=asdict(targets[warp.anchor]),
                )
            result.append(record)
    return result


def validate_catalog_geometry(repo: HgssMapRepo, entries: tuple[HgssMapEntry, ...], scope: str = "johto") -> None:
    for entry in selected_entries(entries, scope):
        header = repo.headers[entry.header]
        blocks = repo.blocks(header)
        if len(blocks) > 256:
            raise ValueError(f"{entry.const} : plus de 256 blocs")
        occupied = {(x, z) for x, z, _, _ in blocks}
        for warp in repo.events(header).warps:
            if (warp.x // 32, warp.z // 32) not in occupied:
                raise ValueError(f"{entry.const} : passage hors des blocs de terrain : {warp}")


def passage_surface(repo: HgssMapRepo, header: int, index: int) -> dict:
    native = repo.headers[header]
    warp = repo.events(native).warps[index]
    blocks = {(x, z): (block, altitude) for x, z, block, altitude in repo.blocks(native)}
    block, altitude = blocks[warp.x // 32, warp.z // 32]
    land = repo.land(block)
    candidates = (
        ()
        if land.bdhc is None
        else heights(land.bdhc, (warp.x % 32 * 16 - 248) * FX_ONE, (warp.z % 32 * 16 - 248) * FX_ONE)
    )
    if candidates:
        values = tuple(height + altitude * 8 * FX_ONE for height in candidates)
        return {"height_fx32": min(values), "candidates_fx32": values, "source": "bdhc"}
    path = _CATALOG.with_name("hgss_warp_heights.csv")
    with path.open(encoding="utf-8", newline="") as handle:
        corrections = tuple(csv.DictReader(handle))
    matching = [row for row in corrections if (int(row["header"]), int(row["index"])) == (header, index)]
    if len(matching) != 1 or not matching[0]["reason"]:
        raise ValueError(f"{native.constant} : passage {index} sans surface BDHC ni correction justifiée")
    return {
        "height_fx32": int(matching[0]["height_units"]) * FX_ONE,
        "candidates_fx32": (),
        "source": "editorial",
        "reason": matching[0]["reason"],
    }


def matrix_neighbors(repo: HgssMapRepo, entries: tuple[HgssMapEntry, ...], scope: str = "johto") -> list[dict]:
    lookup = {entry.header: entry for entry in entries}
    selected = {entry.header for entry in selected_entries(entries, scope)}
    matrix = repo.matrix(next(repo.headers[e.header] for e in entries if e.plan == "johto-exterieurs"))
    if matrix.headers is None:
        raise ValueError("Johto : matrice extérieure sans en-têtes")
    result = []
    for z, row in enumerate(matrix.headers):
        for x, source in enumerate(row):
            if source not in selected or matrix.blocks[z][x] == 0xFFFF:
                continue
            for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, nz = x + dx, z + dz
                if not 0 <= nx < matrix.width or not 0 <= nz < matrix.height:
                    continue
                target = matrix.headers[nz][nx]
                if target == source or target == 0 or matrix.blocks[nz][nx] == 0xFFFF:
                    continue
                if target not in lookup:
                    raise ValueError(f"Johto : voisin de matrice inconnu : {target}")
                result.append(
                    {
                        "source": source,
                        "destination": target,
                        "source_block": (x, z),
                        "target_block": (nx, nz),
                        "target_scope": lookup[target].scope,
                        "target_const": lookup[target].const,
                    }
                )
    return result

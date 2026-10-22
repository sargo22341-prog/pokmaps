"""Coupes des surfaces superposées HGSS, distinctes des étages et des liaisons."""

from pathlib import Path

from .maps_render_hgss import HgssRenderer
from .pret_gen4_land import FX_ONE
from .validate_hgss_maps import surface_grid


def render_layers(
    renderer: HgssRenderer,
    entry: dict,
    folder: Path,
    cache: Path,
) -> tuple[list[dict], list[dict], list[dict]]:
    from .preview_johto_hgss import _render

    cells = [
        cell for cell in surface_grid(renderer.repo, renderer.repo.headers[entry["header"]]) if len(cell["heights"]) > 1
    ]
    # Un pas vertical de matrice vaut huit unités ; les petites intersections BDHC ne créent pas d'étage.
    ceilings = sorted(
        {
            (low + high) // 2
            for cell in cells
            for low, high in zip(cell["heights"][:-1], cell["heights"][1:], strict=True)
            if high - low >= 8 * FX_ONE
        }
    )
    if len(ceilings) > 256:
        raise ValueError(f"{entry['const']} : plus de 256 coupes de terrain")
    minimum = _minimum_geometry_height(renderer, entry["header"]) if ceilings else None
    layers, nonvisual = [], []
    for ceiling in ceilings:
        witnesses = [
            cell
            for cell in cells
            if any(low < ceiling < high for low, high in zip(cell["heights"][:-1], cell["heights"][1:], strict=True))
        ]
        if minimum is not None and ceiling < minimum:
            nonvisual.append(
                dict(
                    ceiling_fx32=ceiling,
                    witnesses=witnesses,
                    kind="below_static_geometry",
                    reason="Surface BDHC sous toute la géométrie visible du lieu",
                )
            )
            continue
        layer = _render(renderer, {**entry, "ceiling_fx32": ceiling}, folder, cache)
        layer["name_fr"] = f"{entry['name_fr']} — coupe à {ceiling / FX_ONE:g} unités"
        layer["witnesses"] = witnesses
        layers.append(layer)
    return cells, layers, nonvisual


def _minimum_geometry_height(renderer: HgssRenderer, header_id: int) -> int:
    header = renderer.repo.headers[header_id]
    values = [
        vertex.position[1]
        for _, _, block, altitude in renderer.repo.blocks(header)
        for vertices, material in renderer.triangles(header, block, altitude)
        if material.alpha
        for vertex in vertices
    ]
    if not values:
        raise ValueError(f"{header.constant} : géométrie visible absente")
    return min(values)

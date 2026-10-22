"""Écarte les surfaces de rencontre masquées par la géométrie HGSS à l'écran."""

from collections import defaultdict

from .maps_raster_gen4 import ONE, RasterCanvas
from .maps_render_hgss import HgssRenderer, camera_cotangent
from .pret_hgss_maps import HgssHeader

_BUCKET = 32
# Une demi-case tolère le décalage du sol visuel (4,23 unités dans les gabarits Safari), jamais un étage.
_DEPTH_TOLERANCE = 8 * ONE


class _SurfaceCanvas(RasterCanvas):
    @property
    def visible_depth(self) -> int | None:
        """Profondeur opaque du pixel à comparer à la surface de collision."""
        return self._depth[0]


def visible_surfaces(renderer: HgssRenderer, record: dict, cells: dict, depths: dict, rejected: list[dict]) -> dict:
    header = renderer.repo.headers[record["header"]]
    cotangent = camera_cotangent(renderer.repo.root, header)
    origin = record["origin_pixels"]
    objects = {point for kind in ("tree", "rock") for point in cells.get(kind, [])}
    points = {point for values in cells.values() for point in values} - objects
    buckets = {(x // _BUCKET, y // _BUCKET) for x, y in points}
    triangles = _bucket_triangles(renderer, header, origin, cotangent, buckets)
    visible = set(objects)
    failures = {}
    for point in sorted(points):
        x, y = point
        canvas = _SurfaceCanvas((x + origin[0], y + origin[1]), (1, 1), cotangent)
        for vertices, material, offset in triangles[(x // _BUCKET, y // _BUCKET)]:
            canvas.triangle(vertices, material, offset)
        depth = canvas.visible_depth
        if depth is not None and abs(depth - depths[point]) <= _DEPTH_TOLERANCE:
            visible.add(point)
        else:
            failures[point] = depth
    result = {}
    for kind, candidates in cells.items():
        accepted = []
        for point in candidates:
            if point in visible:
                accepted.append(point)
            else:
                rejected.append(
                    dict(
                        point=point,
                        kind=kind,
                        reason="profondeur BDHC incompatible avec le décor visible",
                        depth_fx32=depths[point],
                        visible_depth_fx32=failures[point],
                    )
                )
        if accepted:
            result[kind] = accepted
    return result


def _bucket_triangles(
    renderer: HgssRenderer, header: HgssHeader, origin: list[int], cotangent: int, buckets: set
) -> dict:
    result = defaultdict(list)
    for column, row, block, altitude in renderer.repo.blocks(header):
        offset = column * 512, row * 512
        for vertices, material in renderer.triangles(header, block, altitude):
            if not material.alpha:
                continue
            projected = [
                (
                    (v.position[0] // ONE + offset[0] - origin[0]) // _BUCKET,
                    ((v.position[2] - v.position[1] * cotangent // ONE) // ONE + offset[1] - origin[1]) // _BUCKET,
                )
                for v in vertices
            ]
            left, right = min(p[0] for p in projected), max(p[0] for p in projected)
            top, bottom = min(p[1] for p in projected), max(p[1] for p in projected)
            for y in range(top, bottom + 1):
                for x in range(left, right + 1):
                    if (x, y) in buckets:
                        result[x, y].append((vertices, material, offset))
    return result

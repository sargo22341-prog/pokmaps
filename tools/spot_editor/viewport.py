"""Transformation bornée entre les pixels de la carte et ceux de la fenêtre."""

from dataclasses import dataclass

from .catalog import EditorMap

_MIN_ZOOM = 0.25
_MAX_ZOOM = 16.0


@dataclass
class MapViewport:
    zoom: float = 1.0
    scale: float = 1.0
    origin: tuple[float, float] = (0.0, 0.0)
    center: tuple[float, float] | None = None

    def layout(self, editor_map: EditorMap, width: int, height: int) -> None:
        fit = min(width / editor_map.width, height / editor_map.height, 4.0)
        self.scale = fit * self.zoom
        center = self.center or (editor_map.width / 2, editor_map.height / 2)
        self.origin = (width / 2 - center[0] * self.scale, height / 2 - center[1] * self.scale)

    def screen(self, editor_map: EditorMap, point: tuple[float, float]) -> tuple[float, float]:
        return (
            self.origin[0] + (point[0] - editor_map.x) * self.scale,
            self.origin[1] + (point[1] - editor_map.y) * self.scale,
        )

    def map_point(self, editor_map: EditorMap, x: float, y: float) -> tuple[float, float]:
        return (editor_map.x + (x - self.origin[0]) / self.scale, editor_map.y + (y - self.origin[1]) / self.scale)

    def change_zoom(self, factor: float) -> None:
        self.zoom = min(_MAX_ZOOM, max(_MIN_ZOOM, self.zoom * factor))

    def focus(self, editor_map: EditorMap, point: tuple[float, float]) -> None:
        self.center = (point[0] - editor_map.x, point[1] - editor_map.y)

    def pan(self, dx: float, dy: float, editor_map: EditorMap) -> None:
        center = self.center or (editor_map.width / 2, editor_map.height / 2)
        self.center = (
            min(editor_map.width, max(0.0, center[0] - dx / self.scale)),
            min(editor_map.height, max(0.0, center[1] - dy / self.scale)),
        )

"""Zone de dessin : image du lieu à l'échelle de la fenêtre et emplacements par-dessus."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from PIL import Image, ImageTk

from pokemaps_data.map_spots import Point

from .catalog import EditorMap

_MAX_SCALE = 4.0
_DOT_RADIUS = 5
# Un clic à moins de cette distance (pixels d'écran) d'un emplacement le retire.
_HIT_RADIUS = 8


class SpotCanvas:
    """Affiche un lieu et ses emplacements.

    Un clic remonte sa position en pixels de carte et un test qui dit s'il touche un emplacement existant."""

    def __init__(self, parent: tk.Misc, on_click: Callable[[float, float, Callable[[Point], bool]], None]) -> None:
        self.widget = tk.Canvas(parent, background="#222222", highlightthickness=0, cursor="crosshair")
        self.widget.bind("<Configure>", lambda _event: self.draw())
        self.widget.bind("<Button-1>", self._click)
        self._on_click = on_click
        self._map: EditorMap | None = None
        self._image: Image.Image | None = None
        self._points: frozenset[Point] = frozenset()
        self._photo: ImageTk.PhotoImage | None = None
        self._scale = 1.0
        self._origin = (0.0, 0.0)

    def show(self, editor_map: EditorMap | None, image: Image.Image | None, points: frozenset[Point]) -> None:
        self._map, self._image, self._points = editor_map, image, points
        self.draw()

    def draw(self) -> None:
        self.widget.delete("all")
        width, height = self.widget.winfo_width(), self.widget.winfo_height()
        if self._map is None or self._image is None or width < 10 or height < 10:
            return
        self._scale = min(width / self._image.width, height / self._image.height, _MAX_SCALE)
        size = (max(1, round(self._image.width * self._scale)), max(1, round(self._image.height * self._scale)))
        self._origin = ((width - size[0]) / 2, (height - size[1]) / 2)
        self._photo = ImageTk.PhotoImage(self._image.resize(size, Image.Resampling.NEAREST))
        self.widget.create_image(*self._origin, image=self._photo, anchor="nw")
        for point in self._points:
            x, y = self._screen(self._map, point)
            self.widget.create_oval(
                x - _DOT_RADIUS, y - _DOT_RADIUS, x + _DOT_RADIUS, y + _DOT_RADIUS, fill="#ff3158", outline="white"
            )

    def _screen(self, editor_map: EditorMap, point: Point) -> tuple[float, float]:
        return (
            self._origin[0] + (point[0] - editor_map.x) * self._scale,
            self._origin[1] + (point[1] - editor_map.y) * self._scale,
        )

    def _click(self, event: tk.Event) -> None:
        editor_map = self._map
        if editor_map is None or self._image is None:
            return

        def hit(point: Point) -> bool:
            x, y = self._screen(editor_map, point)
            return (x - event.x) ** 2 + (y - event.y) ** 2 <= _HIT_RADIUS**2

        x = editor_map.x + (event.x - self._origin[0]) / self._scale
        y = editor_map.y + (event.y - self._origin[1]) / self._scale
        self._on_click(x, y, hit)

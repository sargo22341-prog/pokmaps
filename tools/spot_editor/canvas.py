"""Carte zoomable, coordonnées du curseur et points à corriger."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from PIL import Image, ImageTk

from pokemaps_data.map_spots import Point

from .catalog import EditorMap
from .viewport import MapViewport

_DOT_RADIUS = 5
_HIT_RADIUS = 8


class SpotCanvas:
    def __init__(self, parent: tk.Misc, on_click: Callable[[float, float, Callable[[Point], bool]], None]) -> None:
        self.widget = ttk.Frame(parent)
        self.canvas = tk.Canvas(self.widget, background="#222222", highlightthickness=0, cursor="crosshair")
        self._on_click = on_click
        self._map: EditorMap | None = None
        self._image: Image.Image | None = None
        self._points: frozenset[Point] = frozenset()
        self._invalid: frozenset[Point] = frozenset()
        self._photo: ImageTk.PhotoImage | None = None
        self.view = MapViewport()
        self._drag = (0, 0)
        self._build_controls()
        self.canvas.pack(fill="both", expand=True)
        self._bind_events()

    def _build_controls(self) -> None:
        bar = ttk.Frame(self.widget, padding=4)
        bar.pack(fill="x", side="bottom")
        ttk.Button(bar, text="−", width=4, command=lambda: self.zoom(1 / 1.25)).pack(side="left")
        ttk.Button(bar, text="+", width=4, command=lambda: self.zoom(1.25)).pack(side="left")
        ttk.Button(bar, text="Ajuster", command=self.reset).pack(side="left", padx=4)
        self.zoom_label = ttk.Label(bar, text="100 %")
        self.zoom_label.pack(side="left")
        self.coordinates = ttk.Label(bar, text="Curseur : —")
        self.coordinates.pack(side="right")

    def _bind_events(self) -> None:
        self.canvas.bind("<Configure>", lambda _event: self.draw())
        self.canvas.bind("<Button-1>", self._click)
        self.canvas.bind("<Motion>", self._motion)
        self.canvas.bind("<Leave>", lambda _event: self.coordinates.configure(text="Curseur : —"))
        self.canvas.bind("<MouseWheel>", self._wheel)
        self.canvas.bind("<Button-4>", lambda event: self._wheel(event, 1.25))
        self.canvas.bind("<Button-5>", lambda event: self._wheel(event, 1 / 1.25))
        self.canvas.bind("<Button-3>", self._start_pan)
        self.canvas.bind("<B3-Motion>", self._pan)

    def show(
        self,
        editor_map: EditorMap | None,
        image: Image.Image | None,
        points: frozenset[Point],
        invalid: frozenset[Point] = frozenset(),
    ) -> None:
        if editor_map != self._map:
            self.view = MapViewport()
        self._map, self._image, self._points, self._invalid = editor_map, image, points, invalid
        self.draw()

    def draw(self) -> None:
        self.canvas.delete("all")
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        if self._map is None or self._image is None or width < 10 or height < 10:
            return
        self.view.layout(self._map, width, height)
        self._draw_image(width, height)
        for point in self._points:
            x, y = self.view.screen(self._map, point)
            radius = _DOT_RADIUS + 3 if point in self._invalid else _DOT_RADIUS
            color = "#ffcc00" if point in self._invalid else "#ff3158"
            self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill=color, outline="white")
            if point in self._invalid:
                self.canvas.create_text(x, y, text="!", fill="black")
        self.zoom_label.configure(text=f"{self.view.zoom * 100:.0f} %")

    def _draw_image(self, width: int, height: int) -> None:
        if self._image is None:
            return
        ox, oy = self.view.origin
        scale = self.view.scale
        # Le bitmap reste borné à la fenêtre même lorsque la carte est fortement agrandie.
        box = (-ox / scale, -oy / scale, (width - ox) / scale, (height - oy) / scale)
        visible = self._image.transform((width, height), Image.Transform.EXTENT, box, Image.Resampling.NEAREST)
        self._photo = ImageTk.PhotoImage(visible)
        self.canvas.create_image(0, 0, image=self._photo, anchor="nw")

    def zoom(self, factor: float) -> None:
        self.view.change_zoom(factor)
        self.draw()

    def reset(self) -> None:
        self.view = MapViewport()
        self.draw()

    def focus(self, point: Point) -> None:
        if self._map is not None:
            self.view.focus(self._map, point)
            self.draw()

    def _motion(self, event: tk.Event) -> None:
        if self._map is None:
            return
        x, y = self.view.map_point(self._map, event.x, event.y)
        cell = self._map.snap(x, y)
        text = f"Curseur : x={int(x)}, y={int(y)}"
        text += f" · Case : {cell[0]}, {cell[1]}" if cell else " · Hors du lieu"
        self.coordinates.configure(text=text)

    def _wheel(self, event: tk.Event, factor: float | None = None) -> None:
        if self._map is None:
            return
        point = self.view.map_point(self._map, event.x, event.y)
        old_scale = self.view.scale
        self.view.change_zoom(factor if factor is not None else (1.25 if event.delta > 0 else 1 / 1.25))
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        self.view.layout(self._map, width, height)
        if self.view.scale != old_scale:
            center = (
                point[0] + (width / 2 - event.x) / self.view.scale,
                point[1] + (height / 2 - event.y) / self.view.scale,
            )
            self.view.focus(self._map, center)
        self.draw()
        self._motion(event)

    def _start_pan(self, event: tk.Event) -> None:
        self._drag = (event.x, event.y)

    def _pan(self, event: tk.Event) -> None:
        if self._map is not None:
            self.view.pan(event.x - self._drag[0], event.y - self._drag[1], self._map)
            self._drag = (event.x, event.y)
            self.draw()
            self._motion(event)

    def _click(self, event: tk.Event) -> None:
        editor_map = self._map
        if editor_map is None or self._image is None:
            return

        def hit(point: Point) -> bool:
            x, y = self.view.screen(editor_map, point)
            return (x - event.x) ** 2 + (y - event.y) ** 2 <= _HIT_RADIUS**2

        x, y = self.view.map_point(editor_map, event.x, event.y)
        self._on_click(x, y, hit)

"""Fenêtre de l'éditeur : choix du jeu, de la région, du lieu et du terrain, édition des emplacements et
enregistrement.

Tant que des jeux sont en cours d'intégration (games.GAMES_IN_PROGRESS), l'éditeur lit l'aperçu de tous les jeux
généré par build_data.py, et non les assets de l'application qui ne les contiennent pas."""

from __future__ import annotations

import queue
import sqlite3
import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox, ttk

from PIL import Image

from pokemaps_data.games import GAMES_IN_PROGRESS
from pokemaps_data.map_spots import SPOTS_CSV, Point, TerrainKey, read_spots, write_spots
from pokemaps_data.sources import PREVIEW_DIR

from .canvas import SpotCanvas
from .catalog import EditorCatalog, EditorMap, EncounterLine, MapMark, required_spots, used_by_app
from .overlays import Layer, OverlayPainter, wild_preview
from .rendering import MapImages
from .session import Shortfall, SpotSession
from .terrain import WildTerrains
from .validation import StepEvent, StepState, run_steps, validation_plan

ROOT = Path(__file__).resolve().parents[2]
ASSETS = PREVIEW_DIR if GAMES_IN_PROGRESS else ROOT / "app/src/main/assets"
DATABASE = ASSETS / "database/pokedex.db"
CACHE = ROOT / "tools/.cache"
TERRAIN_LABELS = {
    "grass": "Herbes hautes (marche)",
    "floor": "Sol des grottes et bâtiments (marche)",
    "water": "Eau (surf et pêche)",
    "tree": "Arbres (Coup d'Boule)",
    "rock": "Rochers (Éclate-Roc)",
}
ALL_REGIONS = "Toutes les régions"
_POLL_MS = 100
_WARNING_COLOR = "#b3261e"


class MapEditor:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.catalog = EditorCatalog(DATABASE)
        self.images = MapImages(ASSETS / "maps")
        self.painter = OverlayPainter(ASSETS)
        self.wild_terrains = WildTerrains(CACHE)
        self.session = SpotSession(read_spots())
        self.families = self.catalog.families()
        if not self.families:
            raise ValueError("Aucun jeu de la base n'appartient à une famille de cartes connue.")
        self.family = self.families[0]
        self.family_maps: list[EditorMap] = []
        self.map_regions: dict[str, str | None] = {}
        self.regions: list[str | None] = []
        self.maps: list[EditorMap] = []
        self.current: EditorMap | None = None
        self.lines: list[EncounterLine] = []
        self.marks: list[MapMark] = []
        # L'aperçu des Pokémon sauvages masque la carte : il ne s'affiche qu'à la demande.
        self.layers = {layer: tk.BooleanVar(value=layer is not Layer.WILD_PREVIEW) for layer in Layer}
        self.generated: dict[str, frozenset[Point]] = {}
        self.terrains: list[str] = []
        self.events: queue.Queue[StepEvent] = queue.Queue()
        self.running = False
        self._build_window()
        self._load_family()

    # --- Construction -----------------------------------------------------------

    def _build_window(self) -> None:
        self.root.title("Pokémaps — éditeur des emplacements sauvages")
        self.root.geometry("1250x800")
        self.root.minsize(900, 600)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self._build_sidebar(ttk.Frame(self.root, padding=10))
        self.canvas = SpotCanvas(self.root, self._click)
        self.canvas.widget.grid(row=0, column=1, sticky="nsew")

    def _build_sidebar(self, side: ttk.Frame) -> None:
        side.grid(row=0, column=0, sticky="ns")
        self.family_choice = self._combobox(side, "Jeux", [family.label for family in self.families])
        self.family_choice.bind("<<ComboboxSelected>>", lambda _event: self._choose_family())
        self.region_choice = self._combobox(side, "Région", [])
        self.region_choice.bind("<<ComboboxSelected>>", lambda _event: self._show_region())
        self.map_choice = self._combobox(side, "Route, lieu ou étage", [])
        self.map_choice.bind("<<ComboboxSelected>>", lambda _event: self._select_map())
        self.terrain_choice = self._combobox(side, "Terrain", [])
        self.terrain_choice.bind("<<ComboboxSelected>>", lambda _event: self._select_terrain())
        ttk.Label(side, text="Pokémon à placer sur ce terrain").pack(anchor="w")
        self.encounters = tk.Listbox(side, width=52, height=12, activestyle="none")
        self.encounters.pack(fill="both", expand=True, pady=(4, 8))
        ttk.Label(side, text="Afficher sur la carte").pack(anchor="w")
        for layer, shown in self.layers.items():
            ttk.Checkbutton(side, text=layer.value, variable=shown, command=self._refresh).pack(anchor="w")
        self.warning = tk.Label(side, text="", foreground=_WARNING_COLOR, wraplength=340, justify="left")
        self.warning.pack(anchor="w", pady=(0, 8))
        hint = "Clique sur la carte pour ajouter un emplacement.\nClique sur un emplacement pour le retirer."
        ttk.Label(side, text=hint, justify="left").pack(anchor="w", pady=(0, 8))
        self.save_button = ttk.Button(side, text="Enregistrer toutes les cartes", command=self._save)
        self.save_button.pack(fill="x")
        self.clear_button = ttk.Button(side, text="Vider ce terrain", command=self._clear_terrain)
        self.clear_button.pack(fill="x", pady=(6, 0))
        self.status = ttk.Label(side, text="", wraplength=340)
        self.status.pack(anchor="w", pady=(8, 0))
        self.family_choice.current(0)

    @staticmethod
    def _combobox(parent: ttk.Frame, label: str, values: list[str]) -> ttk.Combobox:
        ttk.Label(parent, text=label).pack(anchor="w")
        box = ttk.Combobox(parent, state="readonly", values=values, width=44)
        box.pack(fill="x", pady=(0, 8))
        return box

    # --- Sélection ----------------------------------------------------------------

    def _choose_family(self) -> None:
        self.family = self.families[self.family_choice.current()]
        self._load_family()

    def _load_family(self, keep: str | None = None) -> None:
        """Lieux de la famille, et régions où les ranger (le lieu `keep` reste choisi s'il existe encore)."""
        self.family_maps = self.catalog.maps(self.family)
        self.map_regions = {
            found.identifier: self.wild_terrains.region(self.family, found.identifier) for found in self.family_maps
        }
        worlds = self.catalog.world_names(self.family)
        self.regions = [None, *worlds]
        self.region_choice["values"] = [ALL_REGIONS, *worlds.values()]
        region = self.map_regions.get(keep) if keep else None
        self.region_choice.current(self.regions.index(region) if region in self.regions else 0)
        self._show_region(keep)

    def _show_region(self, keep: str | None = None) -> None:
        region = self.regions[self.region_choice.current()]
        self.maps = [
            found for found in self.family_maps if region is None or self.map_regions[found.identifier] == region
        ]
        self.map_choice["values"] = [editor_map.name for editor_map in self.maps]
        if not self.maps:
            self.map_choice.set("")
            self._show(None)
            self.status.configure(text="Aucun lieu avec des rencontres sauvages pour ces jeux.")
            return
        index = next((i for i, editor_map in enumerate(self.maps) if editor_map.identifier == keep), 0)
        self.map_choice.current(index)
        self._select_map()

    def _select_map(self) -> None:
        index = self.map_choice.current()
        if index < 0:
            return
        self._show(self.maps[index])

    def _show(self, editor_map: EditorMap | None) -> None:
        previous = self.terrain_choice.current()
        previous_kind = self.terrains[previous] if 0 <= previous < len(self.terrains) else None
        self.current = editor_map
        self.lines = self.catalog.encounters(editor_map) if editor_map else []
        self.generated = self.catalog.generated_spots(editor_map) if editor_map else {}
        self.marks = self.catalog.marks(editor_map) if editor_map else []
        possible = self.wild_terrains.kinds(self.family, editor_map.identifier) if editor_map else frozenset()
        self.terrains = [
            kind for kind in TERRAIN_LABELS if kind in possible and any(kind in line.terrains for line in self.lines)
        ]
        self.terrain_choice["values"] = [TERRAIN_LABELS[kind] for kind in self.terrains]
        if self.terrains:
            self.terrain_choice.current(self._default_terrain(previous_kind))
        else:
            self.terrain_choice.set("")
        self._select_terrain()

    def _default_terrain(self, previous: str | None) -> int:
        """Terrain précédent s'il existe ici, sinon celui que l'application utilise pour la marche ou l'eau."""
        if previous in self.terrains:
            return self.terrains.index(previous)
        for index, kind in enumerate(self.terrains):
            if self._used(kind):
                return index
        return 0

    def _select_terrain(self) -> None:
        self.encounters.delete(0, tk.END)
        kind = self._kind()
        for line in self.lines:
            if kind in line.terrains:
                self.encounters.insert(tk.END, line.label)
        self._refresh()

    # --- Édition ------------------------------------------------------------------

    def _kind(self) -> str | None:
        index = self.terrain_choice.current()
        return self.terrains[index] if 0 <= index < len(self.terrains) else None

    def _key(self, kind: str) -> TerrainKey | None:
        if self.current is None:
            return None
        return TerrainKey(self.family.identifier, self.current.identifier, kind)

    def _points(self, kind: str) -> frozenset[Point]:
        key = self._key(kind)
        return frozenset() if key is None else self.session.points(key, self.generated.get(kind, frozenset()))

    def _used(self, kind: str) -> bool:
        return used_by_app(kind, bool(self._points("grass")), bool(self._points("floor")))

    def _click(self, x: float, y: float, hit: Callable[[Point], bool]) -> None:
        kind = self._kind()
        if self.running or self.current is None or kind is None:
            return
        point = self.current.snap(x, y)
        key = self._key(kind)
        if point is None or key is None:
            return
        self.session.toggle(key, self.generated.get(kind, frozenset()), point, hit)
        self._refresh()

    def _clear_terrain(self) -> None:
        kind = self._kind()
        key = self._key(kind) if kind else None
        if self.running or key is None or kind is None:
            return
        name = TERRAIN_LABELS[kind].lower()
        if messagebox.askyesno("Vider ce terrain", f"Retirer tous les emplacements « {name} » de ce lieu ?"):
            self.session.clear(key, self.generated.get(kind, frozenset()))
            self._refresh()

    def _refresh(self) -> None:
        kind = self._kind()
        points = self._points(kind) if kind else frozenset()
        self.canvas.show(self.current, self._image(kind, points) if kind else None, points)
        self.warning.configure(text=self._warning(kind, len(points)) if kind else "")
        if self.current is None or kind is None:
            self.status.configure(text="")
            return
        status = f"{TERRAIN_LABELS[kind]} : {len(points)} emplacements"
        if self.session.has_changes:
            status += " — modifications en attente d'enregistrement"
        self.status.configure(text=status)

    def _image(self, kind: str, points: frozenset[Point]) -> Image.Image | None:
        """Image du lieu avec les calques cochés, pour voir ce qui entoure chaque emplacement."""
        if self.current is None:
            return None
        layers = frozenset(layer for layer, shown in self.layers.items() if shown.get())
        pokemon = list(dict.fromkeys(line.pokemon_id for line in self.lines if kind in line.terrains))
        wild = wild_preview(points, pokemon)
        return self.painter.paint(self.images.image(self.current), self.current, self.marks, layers, wild)

    def _warning(self, kind: str, count: int) -> str:
        if not self._used(kind):
            return "Les herbes de ce lieu ont des emplacements : l'application n'utilise pas son sol."
        needed = required_spots(self.lines, kind)
        if count < needed:
            return (
                f"Attention : {count} emplacement(s) pour {needed} Pokémon à placer. "
                "L'application les rangera en grille au milieu du terrain."
            )
        return ""

    # --- Enregistrement et vérifications ------------------------------------------

    def _save(self) -> None:
        if self.running:
            return
        if not self.session.has_changes:
            self.status.configure(text="Aucune modification à enregistrer.")
            return
        shortfalls = self._shortfalls()
        if shortfalls and not messagebox.askyesno("Emplacements insuffisants", _shortfall_text(shortfalls)):
            return
        try:
            write_spots(self.session.merged())
        except OSError as error:
            messagebox.showerror("Enregistrement impossible", f"{SPOTS_CSV}\n\n{error}")
            return
        self.session.mark_written()
        self._start_validation()

    def _shortfalls(self) -> list[Shortfall]:
        """Terrains modifiés, de tous les jeux, qui ont moins d'emplacements que de Pokémon à placer."""
        maps = {
            (family.identifier, found.identifier): found
            for family in self.families
            for found in self.catalog.maps(family)
        }
        return self.session.shortfalls(lambda key: self._required(maps.get((key.family, key.map_identifier)), key))

    def _required(self, editor_map: EditorMap | None, key: TerrainKey) -> tuple[str, int]:
        """Nom du lieu et nombre de Pokémon à placer sur ce terrain (0 si l'application ne l'utilise pas)."""
        if editor_map is None:
            return key.map_identifier, 0
        generated = self.catalog.generated_spots(editor_map)

        def has(kind: str) -> bool:
            terrain = TerrainKey(key.family, key.map_identifier, kind)
            return bool(self.session.points(terrain, generated[kind]))

        if not used_by_app(key.kind, has("grass"), has("floor")):
            return editor_map.name, 0
        return editor_map.name, required_spots(self.catalog.encounters(editor_map), key.kind)

    def _start_validation(self) -> None:
        self.running = True
        self._set_enabled(False)
        self.status.configure(text="Emplacements enregistrés. Génération et vérifications en cours…")
        # La génération remplace pokedex.db : la base ne doit pas rester ouverte (verrou sous Windows).
        self.catalog.close()
        steps = validation_plan(ROOT)
        threading.Thread(target=run_steps, args=(steps, self.events), daemon=True).start()
        self.root.after(_POLL_MS, self._poll_validation)

    def _poll_validation(self) -> None:
        try:
            event = self.events.get_nowait()
        except queue.Empty:
            self.root.after(_POLL_MS, self._poll_validation)
            return
        if event.state is StepState.PROGRESS:
            self.status.configure(text=f"En cours : {event.label}…")
            self.root.after(_POLL_MS, self._poll_validation)
            return
        self._finish_validation(event)

    def _finish_validation(self, event: StepEvent) -> None:
        keep = self.current.identifier if self.current else None
        try:
            self.catalog = EditorCatalog(DATABASE)
            self.families = self.catalog.families()
            self.family = next(family for family in self.families if family.identifier == self.family.identifier)
        except (OSError, sqlite3.Error, StopIteration) as error:
            messagebox.showerror("Base illisible", f"Impossible de rouvrir la base après la génération :\n{error}")
            self.root.destroy()
            return
        self.running = False
        self._set_enabled(True)
        self._load_family(keep)
        if event.state is StepState.SUCCESS:
            self.status.configure(text="Génération et vérifications réussies.")
            messagebox.showinfo("Validation terminée", "Les données ont été générées et vérifiées.")
            return
        self.status.configure(text=f"Échec pendant : {event.label}")
        messagebox.showerror(
            "Validation échouée",
            f"Les emplacements sont enregistrés dans map_spots.csv, mais une étape a échoué.\n\n"
            f"Étape : {event.label}\n\n{event.output}",
        )

    def _set_enabled(self, enabled: bool) -> None:
        for box in (self.family_choice, self.region_choice, self.map_choice, self.terrain_choice):
            box.configure(state="readonly" if enabled else tk.DISABLED)
        for button in (self.save_button, self.clear_button):
            button.configure(state=tk.NORMAL if enabled else tk.DISABLED)

    def _close(self) -> None:
        if self.running and not messagebox.askyesno(
            "Vérifications en cours", "La génération est en cours. Fermer quand même l'éditeur ?"
        ):
            return
        if self.session.has_changes and not messagebox.askyesno(
            "Modifications non enregistrées",
            "Des emplacements modifiés ne sont pas enregistrés. Fermer sans enregistrer ?",
        ):
            return
        self.root.destroy()


def _shortfall_text(shortfalls: list[Shortfall]) -> str:
    lines = "\n".join(
        f"• {item.map_name} — {TERRAIN_LABELS[item.key.kind]} : "
        f"{item.points} emplacement(s) pour {item.required} Pokémon"
        for item in shortfalls
    )
    return (
        f"Ces terrains ont moins d'emplacements que de Pokémon à placer :\n\n{lines}\n\n"
        "L'application les rangera en grille au milieu du terrain. Enregistrer quand même ?"
    )


def main() -> None:
    root = tk.Tk()
    try:
        MapEditor(root)
    except (OSError, sqlite3.Error, ValueError) as error:
        root.destroy()
        raise SystemExit(str(error)) from error
    root.mainloop()

"""Fenêtre de l'éditeur : choix du jeu, de la région, du lieu et du terrain, édition des emplacements et
enregistrement.

Tant que des jeux sont en cours d'intégration (games.GAMES_IN_PROGRESS), l'éditeur lit l'aperçu de tous les jeux
généré par build_data.py, et non les assets de l'application qui ne les contiennent pas."""

from __future__ import annotations

import sqlite3
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox, ttk

from PIL import Image

from pokemaps_data.games import GAMES_IN_PROGRESS
from pokemaps_data.map_spots import SPOTS_CSV, Point, TerrainKey, read_spots, selected_key
from pokemaps_data.sources import PREVIEW_DIR

from .canvas import SpotCanvas
from .catalog import EditorCatalog, EditorMap, EncounterLine, Family, MapMark, required_spots, used_by_app
from .coverage import PlacementNeeds, Shortfall
from .error_panel import ErrorPanel
from .overlays import Layer, OverlayPainter, wild_preview
from .rendering import MapImages
from .session import SpotSession
from .terrain import WildTerrains
from .validation import SpotError, save_spots, spot_errors, write_errors
from .version_choice import VersionChoice
from .warning_panel import WarningPanel

ROOT = Path(__file__).resolve().parents[2]
ASSETS = PREVIEW_DIR if GAMES_IN_PROGRESS else ROOT / "app/src/main/assets"
DATABASE = ASSETS / "database/pokedex.db"
CACHE = ROOT / "tools/.cache"
ERROR_REPORT = ROOT / "tools/build/map_spot_errors.json"
TERRAIN_LABELS = {
    "grass": "Herbes hautes (marche)",
    "floor": "Sol des grottes et bâtiments (marche)",
    "water": "Eau (surf et pêche)",
    "tree": "Arbres (Coup d'Boule)",
    "rock": "Rochers (Éclate-Roc)",
}
ALL_REGIONS = "Toutes les régions"
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
        self.errors: list[SpotError] = []
        self.warnings: list[Shortfall] = []
        self.needs = PlacementNeeds(self.catalog, self.families, self.wild_terrains)
        self._build_window()
        self._load_family()
        self._update_errors()
        self._refresh()

    # --- Construction -----------------------------------------------------------

    def _build_window(self) -> None:
        self.root.title("Pokémaps — éditeur des emplacements sauvages")
        self.root.geometry("1250x800")
        self.root.minsize(900, 600)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self._build_sidebar(ttk.Frame(self.root, padding=10))
        right = ttk.Frame(self.root)
        right.grid(row=0, column=1, sticky="nsew")
        self.error_panel = ErrorPanel(right, self._go_to_error, self._remove_error)
        self.error_panel.widget.pack(fill="x", pady=(0, 4))
        self.warning_panel = WarningPanel(right, self._go_to_warning)
        self.warning_panel.widget.pack(fill="x", pady=(0, 4))
        self.canvas = SpotCanvas(right, self._click)
        self.canvas.widget.pack(fill="both", expand=True)

    def _build_sidebar(self, side: ttk.Frame) -> None:
        side.grid(row=0, column=0, sticky="ns")
        self.family_choice = self._combobox(side, "Jeux", [family.label for family in self.families])
        self.family_choice.bind("<<ComboboxSelected>>", lambda _event: self._choose_family())
        self.version_choice = VersionChoice(side, self._select_map, self._refresh)
        self.region_choice = self._combobox(side, "Région", [])
        self.region_choice.bind("<<ComboboxSelected>>", lambda _event: self._show_region())
        self.map_choice = self._combobox(side, "Route, lieu ou étage", [])
        self.map_choice.bind("<<ComboboxSelected>>", lambda _event: self._select_map())
        self.terrain_choice = self._combobox(side, "Terrain", [])
        self.terrain_choice.bind("<<ComboboxSelected>>", lambda _event: self._select_terrain())
        ttk.Label(side, text="Pokémon à placer sur ce terrain").pack(anchor="w")
        self.encounters = tk.Listbox(side, width=52, height=7, activestyle="none")
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
        self.version_choice.show(self.family)
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
        if editor_map is not None:
            editor_map = self.catalog.version_map(self.family, editor_map.identifier, self.version_choice.group)
        previous = self.terrain_choice.current()
        previous_kind = self.terrains[previous] if 0 <= previous < len(self.terrains) else None
        self.current = editor_map
        self.lines = self.catalog.encounters(editor_map) if editor_map else []
        self.generated = self.catalog.generated_spots(editor_map) if editor_map else {}
        self.marks = self.catalog.marks(editor_map) if editor_map else []
        possible = (
            self.wild_terrains.kinds(self._editing_family(), editor_map.identifier) if editor_map else frozenset()
        )
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
        group = self.version_choice.group if self.version_choice.only_displayed.get() else ""
        return TerrainKey(self.family.identifier, self.current.identifier, kind, group)

    def _editing_family(self) -> Family:
        groups = (
            (self.version_choice.group,) if self.version_choice.only_displayed.get() else self.family.version_groups
        )
        return Family(self.family.identifier, self.family.label, groups)

    def _generated(self, kind: str) -> frozenset[Point]:
        if self.current is None:
            return frozenset()
        common = TerrainKey(self.family.identifier, self.current.identifier, kind)
        return self.session.points(common, self.generated.get(kind, frozenset()))

    def _points(self, kind: str) -> frozenset[Point]:
        key = self._key(kind)
        return frozenset() if key is None else self.session.points(key, self._generated(kind))

    def _used(self, kind: str) -> bool:
        return used_by_app(kind, bool(self._points("grass")), bool(self._points("floor")))

    def _click(self, x: float, y: float, hit: Callable[[Point], bool]) -> None:
        kind = self._kind()
        if self.current is None or kind is None:
            return
        point = self.current.snap(x, y)
        key = self._key(kind)
        if point is None or key is None:
            return
        points = self._points(kind)
        removing = any(hit(existing) for existing in points)
        if not removing and point not in self.wild_terrains.points(
            self._editing_family(), self.current.identifier, kind
        ):
            self.status.configure(text="Cette case n'appartient pas au terrain choisi dans les jeux ciblés.")
            return
        self.session.toggle(key, self._generated(kind), point, hit)
        self._update_errors()
        self._refresh()

    def _clear_terrain(self) -> None:
        kind = self._kind()
        key = self._key(kind) if kind else None
        if key is None or kind is None:
            return
        name = TERRAIN_LABELS[kind].lower()
        if messagebox.askyesno("Vider ce terrain", f"Retirer tous les emplacements « {name} » de ce lieu ?"):
            self.session.clear(key, self._generated(kind))
            self._update_errors()
            self._refresh()

    def _refresh(self) -> None:
        kind = self._kind()
        points = self._points(kind) if kind else frozenset()
        key = self._key(kind) if kind else None
        if key is not None and key.version_group:
            key = selected_key(self.session.merged(), key, key.version_group)
        invalid = frozenset(error.point for error in self.errors if error.key == key and error.point)
        self.canvas.show(self.current, self._image(kind, points) if kind else None, points, invalid)
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
        if needed and not count:
            return f"Erreur : aucun emplacement pour {needed} Pokémon à placer, aucun ne serait affiché."
        if count < needed:
            return (
                f"Attention : {count} emplacement(s) pour {needed} Pokémon à placer. L'application affichera un "
                "Pokémon tiré au hasard par emplacement ; les autres seront visibles dans la liste seulement."
            )
        return ""

    # --- Enregistrement et vérifications ------------------------------------------

    def _update_errors(self) -> None:
        shortfalls = self.needs.shortfalls(self.session)
        self.warnings = [item for item in shortfalls if not item.blocking]
        empty = [SpotError(item.key, None, item.message, item.version_group) for item in shortfalls if item.blocking]
        self.errors = spot_errors(self.session, self.families, self.wild_terrains) + empty
        self.error_panel.show(self.errors)
        self.warning_panel.show(self.warnings)
        try:
            write_errors(self.errors, ERROR_REPORT)
        except OSError as error:
            messagebox.showerror("Rapport d'erreurs non enregistré", f"{ERROR_REPORT}\n\n{error}")

    def _go_to_error(self, error: SpotError) -> None:
        self._go_to(error.key, error.version_group, error.point, error.label)

    def _go_to_warning(self, warning: Shortfall) -> None:
        self._go_to(warning.key, warning.version_group, None, warning.label)

    def _go_to(self, key: TerrainKey, version_group: str, point: Point | None, label: str) -> None:
        """Ouvre le lieu et le terrain de `key`, sur le plan de `version_group` (ou du groupe de `key`)."""
        index = next((i for i, family in enumerate(self.families) if family.identifier == key.family), None)
        if index is None:
            return
        self.family_choice.current(index)
        self.family = self.families[index]
        self._load_family(key.map_identifier)
        shown = key.version_group or version_group
        if shown:
            self.version_choice.select(shown)
            self._select_map()
        self.version_choice.only_displayed.set(bool(key.version_group))
        if self.current is None or self.current.identifier != key.map_identifier:
            self.status.configure(text="Cette carte est absente de la base de l'éditeur.")
            return
        if key.kind not in self.terrains:
            self.terrains.append(key.kind)
            self.terrain_choice["values"] = [TERRAIN_LABELS[kind] for kind in self.terrains]
        self.terrain_choice.current(self.terrains.index(key.kind))
        self._select_terrain()
        if point is not None:
            self.canvas.focus(point)
        self.status.configure(text=label)

    def _remove_error(self, error: SpotError) -> None:
        if error.point is None:
            self._go_to_error(error)
            return
        self.session.remove(error.key, frozenset(), error.point)
        self._update_errors()
        self._refresh()

    def _save(self) -> None:
        self._update_errors()
        if self.errors:
            self.status.configure(text=f"{len(self.errors)} erreur(s) : cliquez dans la liste pour les corriger.")
            return
        if not self.session.has_changes:
            self.status.configure(text="Aucune modification à enregistrer.")
            return
        try:
            save_spots(self.session, self.families, self.wild_terrains, SPOTS_CSV)
        except (OSError, ValueError) as error:
            messagebox.showerror("Enregistrement impossible", f"{SPOTS_CSV}\n\n{error}")
            return
        self._refresh()
        self.status.configure(text="Emplacements enregistrés dans map_spots.csv.")
        messagebox.showinfo(
            "Enregistrement terminé", "Les emplacements ont été enregistrés, sans génération de données."
        )

    def _close(self) -> None:
        if self.session.has_changes and not messagebox.askyesno(
            "Modifications non enregistrées",
            "Des emplacements modifiés ne sont pas enregistrés. Fermer sans enregistrer ?",
        ):
            return
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    try:
        MapEditor(root)
    except (OSError, sqlite3.Error, ValueError) as error:
        root.destroy()
        raise SystemExit(str(error)) from error
    root.mainloop()

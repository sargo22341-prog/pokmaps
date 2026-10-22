"""Choix du plan affiché et de la portée des emplacements édités."""

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from .catalog import Family

VERSION_LABELS = {
    "heartgold-soulsilver": "Or HeartGold / Argent SoulSilver",
    "red-blue": "Rouge / Bleu",
    "yellow": "Jaune",
    "gold-silver": "Or / Argent",
    "crystal": "Cristal",
    "ruby-sapphire": "Rubis / Saphir",
    "emerald": "Émeraude",
    "firered-leafgreen": "Rouge Feu / Vert Feuille",
    "diamond-pearl": "Diamant / Perle",
    "platinum": "Platine",
}


class VersionChoice:
    def __init__(self, parent: tk.Misc, on_change: Callable[[], None], on_scope: Callable[[], None]) -> None:
        ttk.Label(parent, text="Carte affichée").pack(anchor="w")
        self.choice = ttk.Combobox(parent, state="readonly", width=44)
        self.choice.pack(fill="x", pady=(0, 4))
        # Les points propres à un groupe restent rares : par défaut, on édite les points communs à la famille.
        self.only_displayed = tk.BooleanVar(value=False)
        self.check = ttk.Checkbutton(parent, variable=self.only_displayed, command=on_scope)
        self.check.pack(anchor="w", pady=(0, 8))
        self.groups: tuple[str, ...] = ()
        self._on_change = on_change
        self.choice.bind("<<ComboboxSelected>>", self._changed)

    @property
    def group(self) -> str:
        return self.groups[self.choice.current()]

    def show(self, family: Family, groups: tuple[str, ...] | None = None) -> None:
        previous = self.group if self.groups else ""
        self.groups = family.version_groups if groups is None else groups
        if not self.groups:
            raise ValueError("Aucun jeu disponible pour cette carte.")
        self.choice["values"] = [VERSION_LABELS[group] for group in self.groups]
        self.select(previous if previous in self.groups else self.groups[0])

    def select(self, group: str) -> None:
        self.choice.current(self.groups.index(group))
        self.check.configure(text=f"Points uniquement pour {VERSION_LABELS[group]}")

    def _changed(self, _event: tk.Event) -> None:
        self.select(self.group)
        self._on_change()

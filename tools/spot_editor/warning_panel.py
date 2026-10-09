"""Liste repliable des avertissements (terrains qui manquent d'emplacements) et navigation vers le terrain."""

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from .coverage import Shortfall

_WARNING_COLOR = "#8a5300"


class WarningPanel:
    """Repliée par défaut : les avertissements n'empêchent pas d'enregistrer."""

    def __init__(self, parent: tk.Misc, on_select: Callable[[Shortfall], None]) -> None:
        self.widget = ttk.Frame(parent)
        self.toggle = ttk.Button(self.widget, command=self._toggle)
        self.toggle.pack(fill="x")
        self.body = ttk.Frame(self.widget, padding=(0, 4, 0, 0))
        self.body.columnconfigure(0, weight=1)
        self.list = tk.Listbox(self.body, height=6, exportselection=False, foreground=_WARNING_COLOR)
        self.list.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(self.body, command=self.list.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.list.configure(yscrollcommand=scroll.set)
        self.list.bind("<<ListboxSelect>>", self._select)
        self.expanded = False
        self._on_select = on_select
        self._warnings: list[Shortfall] = []
        self._update_title()

    def show(self, warnings: list[Shortfall]) -> None:
        if warnings == self._warnings:
            return
        self._warnings = list(warnings)
        self.list.delete(0, tk.END)
        for warning in warnings:
            self.list.insert(tk.END, warning.label)
        self._update_title()

    def _toggle(self) -> None:
        self.expanded = not self.expanded
        if self.expanded:
            self.body.pack(fill="x")
        else:
            self.body.pack_forget()
        self._update_title()

    def _update_title(self) -> None:
        arrow = "▾" if self.expanded else "▸"
        self.toggle.configure(text=f"{arrow} Avertissements ({len(self._warnings)}) — cliquer pour aller au terrain")

    def _select(self, _event: tk.Event) -> None:
        selection = self.list.curselection()
        if selection and selection[0] < len(self._warnings):
            self._on_select(self._warnings[selection[0]])

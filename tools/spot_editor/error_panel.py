"""Liste des erreurs de placement et navigation vers le point à corriger."""

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from .validation import SpotError


class ErrorPanel:
    def __init__(
        self, parent: tk.Misc, on_select: Callable[[SpotError], None], on_remove: Callable[[SpotError], None]
    ) -> None:
        self.widget = ttk.LabelFrame(parent, text="Erreurs à corriger", padding=4)
        self.widget.columnconfigure(0, weight=1)
        self.widget.rowconfigure(0, weight=1)
        self.list = tk.Listbox(self.widget, height=5, exportselection=False, foreground="#b3261e")
        self.list.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(self.widget, command=self.list.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.list.configure(yscrollcommand=scroll.set)
        self.list.bind("<<ListboxSelect>>", self._select)
        self._on_select = on_select
        self._on_remove = on_remove
        self._errors: list[SpotError] = []
        ttk.Button(self.widget, text="Retirer le point sélectionné", command=self._remove).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(4, 0)
        )

    def show(self, errors: list[SpotError]) -> None:
        if errors == self._errors:
            return
        self._errors = list(errors)
        self.list.delete(0, tk.END)
        for error in errors:
            self.list.insert(tk.END, error.label)
        self.widget.configure(text=f"Erreurs à corriger ({len(errors)}) — cliquer pour aller au point")

    def _select(self, _event: tk.Event) -> None:
        selection = self.list.curselection()
        if selection and selection[0] < len(self._errors):
            self._on_select(self._errors[selection[0]])

    def _remove(self) -> None:
        selection = self.list.curselection()
        if selection and selection[0] < len(self._errors):
            self._on_remove(self._errors[selection[0]])

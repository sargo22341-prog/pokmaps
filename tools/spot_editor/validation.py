"""Génération des données et contrôles Python lancés après un enregistrement, dans un fil séparé."""

from __future__ import annotations

import importlib.util
import os
import queue
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Une étape bloquée (réseau, disque) ne doit pas figer l'éditeur indéfiniment.
_STEP_TIMEOUT_S = 1800
# Fin de sortie gardée pour la fenêtre d'erreur : l'erreur utile est à la fin.
_OUTPUT_TAIL = 6000


class StepState(Enum):
    PROGRESS = "progress"
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True)
class Step:
    label: str
    cwd: Path
    command: tuple[str, ...]


@dataclass(frozen=True)
class StepEvent:
    state: StepState
    label: str
    output: str = ""


def validation_plan(root: Path) -> tuple[Step, ...]:
    """Étapes à lancer ; Ruff et pytest sont d'abord installés (versions épinglées) s'ils manquent."""
    tools = root / "tools"
    steps = [
        Step("Génération des données", root, (sys.executable, "tools/build_data.py")),
        Step("Contrôle Ruff", tools, (sys.executable, "-m", "ruff", "check", ".")),
        Step("Format Ruff", tools, (sys.executable, "-m", "ruff", "format", "--check", ".")),
        Step("Tests Python", tools, (sys.executable, "-m", "pytest", "-q")),
        Step("Tests du pipeline", tools, (sys.executable, "-m", "pytest", "-q", "-m", "pipeline")),
    ]
    if any(importlib.util.find_spec(module) is None for module in ("ruff", "pytest")):
        install = (sys.executable, "-m", "pip", "install", "-r", "tools/requirements-dev.txt")
        steps.insert(0, Step("Installation des outils manquants", root, install))
    return tuple(steps)


def run_steps(steps: tuple[Step, ...], events: queue.Queue[StepEvent]) -> None:
    """Lance les étapes dans l'ordre et s'arrête à la première qui échoue ; publie chaque avancée dans `events`."""
    for step in steps:
        events.put(StepEvent(StepState.PROGRESS, step.label))
        try:
            result = subprocess.run(
                step.command,
                cwd=step.cwd,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                # Sous Windows, Python écrit sinon dans la page de code de la console : accents illisibles.
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                timeout=_STEP_TIMEOUT_S,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            events.put(StepEvent(StepState.FAILURE, step.label, str(error)))
            return
        if result.returncode != 0:
            output = (result.stdout + result.stderr).strip()[-_OUTPUT_TAIL:]
            events.put(StepEvent(StepState.FAILURE, step.label, output or f"Code de sortie {result.returncode}"))
            return
    events.put(StepEvent(StepState.SUCCESS, "Terminé"))

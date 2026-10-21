#!/usr/bin/env python3
"""Lance les contrôles du dépôt sans régénérer les données, avec leurs durées."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_TIMEOUT_SECONDS = 30 * 60


@dataclass(frozen=True)
class _Check:
    name: str
    command: tuple[str, ...]
    directory: Path
    timeout_seconds: int = _TIMEOUT_SECONDS


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("all", "android", "python"), default="all", help="partie à vérifier")
    parser.add_argument("--pipeline", action="store_true", help="ajouter les tests des sources épinglées locales")
    args = parser.parse_args()
    if args.pipeline and args.scope == "android":
        parser.error("--pipeline nécessite --scope python ou all")
    return args


def _checks(scope: str, pipeline: bool) -> list[_Check]:
    checks = []
    if scope in ("all", "python"):
        tools = _ROOT / "tools"
        checks.extend(
            (
                _Check("Assets versionnés", (sys.executable, "tools/check_assets.py"), _ROOT),
                _Check("Ruff", (sys.executable, "-m", "ruff", "check", "."), tools),
                _Check("Format Python", (sys.executable, "-m", "ruff", "format", "--check", "."), tools),
                _Check("Tests Python", (sys.executable, "-m", "pytest", "-q", "--durations=20"), tools),
            )
        )
        if pipeline:
            command = (sys.executable, "-m", "pytest", "-q", "-m", "pipeline", "--durations=20", "--capture=tee-sys")
            checks.append(_Check("Tests des sources épinglées", command, tools, 90 * 60))
    if scope in ("all", "android"):
        wrapper = "gradlew.bat" if os.name == "nt" else "gradlew"
        tasks = ("ktlintCheck", "checkNoGoogleServices", "lintDebug", "testDebugUnitTest", "assembleDebug")
        command = (str(_ROOT / wrapper), *tasks, "--profile", "--console=plain")
        checks.append(_Check("Android : style, dépendances, Lint, tests et APK", command, _ROOT))
    return checks


def main() -> int:
    args = _arguments()
    for check in _checks(args.scope, args.pipeline):
        print(f"\n{check.name}", flush=True)
        started = time.perf_counter()
        try:
            result = subprocess.run(check.command, cwd=check.directory, timeout=check.timeout_seconds, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            print(f"Échec de {check.name} : {error}", file=sys.stderr)
            return 1
        elapsed = time.perf_counter() - started
        print(f"{check.name} : {elapsed:.1f} s (code {result.returncode})", flush=True)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

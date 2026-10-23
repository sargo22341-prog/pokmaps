"""Source HGSS épinglée ; conserver le commit git requis par les contrats de qualification."""

import subprocess
from pathlib import Path

from .sources import HGSS_PRET_COMMIT, PRET_GIT_TIMEOUT_SECONDS, PRET_URL


def fetch_hgss(cache: Path) -> Path:
    target = cache / "hgss-qualification"
    if not target.exists():
        target.mkdir(parents=True)
        _git(target, "init", "-q")
        _git(target, "fetch", "-q", "--depth", "1", PRET_URL.format(repo="pokeheartgold"), HGSS_PRET_COMMIT)
        _git(target, "checkout", "-q", "FETCH_HEAD")
    current = _git(target, "rev-parse", "HEAD").stdout.strip()
    if current != HGSS_PRET_COMMIT:
        raise ValueError(f"HGSS : commit du cache différent du contrat épinglé : {current}")
    (target / ".complete").touch()
    return target


def _git(target: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(target), *arguments],
        check=True,
        capture_output=True,
        text=True,
        timeout=PRET_GIT_TIMEOUT_SECONDS,
        stdin=subprocess.DEVNULL,
    )

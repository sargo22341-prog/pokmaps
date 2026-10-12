"""Exporte les ensembles publics Pokémon ; aucune donnée de compte n'est conservée."""

import argparse
import getpass
import hashlib
import io
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO

_ENDPOINT = "https://retroachievements.org/API/"
_MAX_BYTES = 8_000_000
_MAIN_SERIES = re.compile(
    r"Pokémon (?:Red|Blue|Yellow|Gold|Silver|Crystal|Ruby|Sapphire|Emerald|FireRed|LeafGreen|"
    r"Diamond|Pearl|Platinum|HeartGold|SoulSilver|Black|White|Black 2|White 2|X|Y|"
    r"Omega Ruby|Alpha Sapphire|Sun|Moon|Ultra Sun|Ultra Moon)(?: Version)?(?: 2)?"
    r"(?:: Special Pikachu Edition| \| Pokémon SoulSilver Version)?$"
)


def _request(endpoint: str, key: str, parameters: dict[str, int]) -> list[dict[str, Any]] | dict[str, Any]:
    query = urllib.parse.urlencode({"y": key, **parameters})
    request = urllib.request.Request(
        f"{_ENDPOINT}{endpoint}.php?{query}",
        headers={"User-Agent": "Pokemaps/1.0 (public achievement snapshot)", "Accept": "application/json"},
    )
    content = _read(request, endpoint)
    if len(content) > _MAX_BYTES:
        raise ValueError(f"RetroAchievements : réponse trop grande pour {endpoint}")
    return json.loads(content)


def _read(request: urllib.request.Request, endpoint: str) -> bytes:
    for attempt in range(3):
        time.sleep(1)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return _read_content(response)
        except (urllib.error.URLError, TimeoutError) as error:
            # L'URL authentifiée ne doit jamais apparaître dans un message d'erreur.
            code = getattr(error, "code", "réseau")
            if code == 429 and attempt < 2:
                time.sleep(10)
                continue
            raise ValueError(f"RetroAchievements : échec {code} pour {endpoint}") from None
    raise ValueError(f"RetroAchievements : tentatives épuisées pour {endpoint}")


def _read_content(response: BinaryIO) -> bytes:
    deadline = time.monotonic() + 30
    output = io.BytesIO()
    while output.tell() <= _MAX_BYTES:
        if time.monotonic() > deadline:
            raise TimeoutError("Lecture RetroAchievements expirée")
        chunk = response.read(8192)
        if not chunk:
            return output.getvalue()
        output.write(chunk)
    raise ValueError("RetroAchievements : réponse trop grande")


def _snapshot(game: dict[str, Any], date: str) -> dict[str, Any]:
    if type(game["ID"]) is not int or game["ID"] <= 0 or game.get("ParentGameID") is not None:
        raise ValueError("Ensemble RetroAchievements principal attendu")
    achievements = sorted(game["Achievements"].values(), key=lambda row: (row["DisplayOrder"], row["ID"]))
    if len(achievements) != game["NumAchievements"] or len(achievements) > 500:
        raise ValueError(f"Nombre de succès invalide : {game['ID']}")
    fields = ("ID", "Title", "Description", "Points", "DisplayOrder", "type", "DateModified")
    rows = [{field: row[field] for field in fields} for row in achievements]
    if len({row["ID"] for row in rows}) != len(rows):
        raise ValueError(f"Identifiant de succès répété : {game['ID']}")
    if any(not _valid_achievement(row) for row in rows):
        raise ValueError(f"Succès invalide : {game['ID']}")
    return {
        "game_id": game["ID"],
        "title": game["Title"],
        "console": game["ConsoleName"],
        "source": f"https://retroachievements.org/game/{game['ID']}",
        "exported_at": date,
        "achievements": rows,
    }


def _valid_achievement(row: dict[str, Any]) -> bool:
    return (
        type(row["ID"]) is int
        and row["ID"] > 0
        and type(row["Points"]) is int
        and row["Points"] >= 0
        and type(row["DisplayOrder"]) is int
        and isinstance(row["Title"], str)
        and bool(row["Title"].strip())
        and isinstance(row["Description"], str)
        and bool(row["Description"].strip())
        and isinstance(row["DateModified"], str)
        and bool(row["DateModified"].strip())
        and row["type"] in {None, "missable", "progression", "win_condition"}
    )


def _write(path: Path, content: dict[str, Any]) -> None:
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def export(output: Path, key: str) -> None:
    systems = _request("API_GetConsoleIDs", key, {"a": 1, "g": 1})
    names = {"Game Boy", "Game Boy Color", "Game Boy Advance", "Nintendo DS", "Nintendo 3DS"}
    handhelds = [row for row in systems if row["Name"] in names]
    if len(handhelds) > len(names) or len({row["ID"] for row in handhelds}) != len(handhelds):
        raise ValueError("Catalogue des consoles RetroAchievements invalide")
    date = datetime.now(UTC).isoformat(timespec="seconds")
    games: list[dict[str, Any]] = []
    for system in handhelds:
        catalog = _request("API_GetGameList", key, {"i": system["ID"]})
        games.extend(row for row in catalog if _MAIN_SERIES.fullmatch(row["Title"]))
    if len(games) > 50 or len({row["ID"] for row in games}) != len(games):
        raise ValueError("Catalogue de jeux RetroAchievements invalide")
    if not {724, 586, 723, 576, 722, 810, 790, 791, 668, 515, 788}.issubset({row["ID"] for row in games}):
        raise ValueError("Catalogue incomplet : au moins un des onze jeux distribués est absent")
    output.mkdir(parents=True, exist_ok=True)
    index = []
    for game in sorted(games, key=lambda row: row["ID"]):
        snapshot = _snapshot(_request("API_GetGameExtended", key, {"i": game["ID"]}), date)
        if snapshot["game_id"] != game["ID"]:
            raise ValueError(f"Ensemble RetroAchievements inattendu : {game['ID']}")
        path = output / f"{game['ID']}.json"
        _write(path, snapshot)
        metadata = {field: snapshot[field] for field in ("game_id", "title", "console", "source")}
        metadata["achievement_count"] = len(snapshot["achievements"])
        metadata["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        index.append(metadata)
        print(f"{game['ID']} : {len(snapshot['achievements'])} succès")
    _write(output / "index.json", {"exported_at": date, "games": index})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "data" / "retroachievements")
    arguments = parser.parse_args()
    key = os.environ.get("RETROACHIEVEMENTS_API_KEY") or getpass.getpass("Clé API RetroAchievements : ")
    if not key:
        parser.error("Clé API requise")
    export(arguments.output, key)


if __name__ == "__main__":
    main()

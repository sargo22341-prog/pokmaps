"""Validation hors cache des données propres au Souterrain et aux installations DS."""

from __future__ import annotations


def validate_extras(value: dict, platinum: bool) -> None:
    underground = value["underground"]
    goods, traps, mining = underground["goods"], underground["traps"], value["mining"]
    _identities(goods, "id", set(range(7, 139)), "mobilier")
    trap_ids = set(range(1, 9)) | set(range(11, 15)) | set(range(18, 32)) | {33}
    _identities(traps, "id", trap_ids, "pièges")
    _identities(mining, "id", set(range(1, 60)) - {22}, "fouilles")
    for row in goods + traps:
        if not (
            row["name"].strip()
            and 0 <= row["sphere"] <= 6
            and 0 <= row["min_size"] <= row["max_size"] <= 99
            and (row["sphere"] == 0 or row["min_size"] < row["max_size"])
        ):
            raise ValueError(f"Sinnoh : prix souterrain invalide : {row}")
    for row in mining:
        if not (row["name"].strip() and len(row["weights"]) == 4 and all(0 <= i <= 1000 for i in row["weights"])):
            raise ValueError(f"Sinnoh : objet enfoui invalide : {row}")
    battles = value["battles"]
    _sets(battles["sets"], 950)
    pools = battles["trainers"]
    if len(pools) != (315 if platinum else 307):
        raise ValueError("Sinnoh : nombre de dresseurs de combat invalide")
    for i, pool in enumerate(pools):
        if len(pool) > 100 or any(not 1 <= number <= 950 for number in pool):
            raise ValueError(f"Sinnoh : réserve de combat invalide : {i}")
        if not pool and (not platinum or i not in {307, 308, 309, 310}):
            raise ValueError(f"Sinnoh : réserve de combat absente : {i}")
    _series(battles["tower_ranges"])
    if ("frontier" in battles) != platinum:
        raise ValueError("Sinnoh : Zone de Combat attribuée à la mauvaise version")
    if platinum:
        _frontier(battles["frontier"])


def _identities(rows: list[dict], key: str, expected: set, subject: str) -> None:
    if len(rows) != len(expected) or {row[key] for row in rows} != expected:
        raise ValueError(f"Sinnoh : {subject} incomplet ou répété")


def _sets(rows: list[dict], count: int) -> None:
    _identities(rows, "id", set(range(1, count + 1)), "configurations de combat")
    for row in rows:
        if not (
            1 <= row["species"] <= 493
            and row["name"].strip()
            and len(row["moves"]) == 4
            and all(0 <= number <= 467 for number in row["moves"])
            and len(row["move_names"]) == sum(bool(number) for number in row["moves"])
            and all(name.strip() for name in row["move_names"])
            and 0 <= row["nature"] <= 24
            and row["nature_name"].strip()
            and 0 <= row["evs"] <= 63
            and 0 <= row["form"] <= 5
        ):
            raise ValueError(f"Sinnoh : configuration de combat invalide : {row}")


def _series(rows: list[dict]) -> None:
    if [row["series"] for row in rows] != list(range(1, 9)):
        raise ValueError("Sinnoh : huit séries de combat ordonnées attendues")
    for row in rows:
        for key in ("ordinary", "last"):
            _range(row[key], 0, 299)


def _range(values: list[int], minimum: int, maximum: int) -> None:
    if len(values) != 2 or not minimum <= values[0] <= values[1] <= maximum:
        raise ValueError(f"Sinnoh : intervalle invalide : {values}")


def _frontier(value: dict) -> None:
    if set(value["ranges"]) != {"factory", "castle", "arcade"}:
        raise ValueError("Platine : installations incomplètes")
    for rows in value["ranges"].values():
        _series(rows)
    if set(value["factory"]) != {"level50", "open_player", "open_opponent"}:
        raise ValueError("Platine : modes de location incomplets")
    for rows in value["factory"].values():
        if len(rows) != 10:
            raise ValueError("Platine : dix réserves de location attendues")
        for row in rows:
            _range([row["min"], row["max"]], 1, 950)
            if not 0 <= row["ivs"] <= 31 or not 1 <= row["trainer_limit"] <= 311:
                raise ValueError(f"Platine : réserve de location invalide : {row}")
    _sets(value["hall"]["sets"], 477)
    if len(value["hall"]["ranks"]) != 10:
        raise ValueError("Platine : dix rangs de la Scène attendus")
    for pair in value["hall"]["ranks"]:
        _range(pair, 1, 477)

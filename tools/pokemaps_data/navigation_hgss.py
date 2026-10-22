"""Inventaire des déplacements scriptés HGSS, avec provenance et branches conservées."""

import re
from pathlib import Path

from .pret_gen4_source import read_text
from .pret_hgss_maps import HgssMapRepo

_COMMANDS = frozenset(("Warp", "SetDynamicWarp", "MoveWarp", "ScrCmd_722", "ScrCmd_723"))


def script_navigation(repo: HgssMapRepo, selected: set[int]) -> list[dict]:
    names = {h.constant: h.index for h in repo.headers.values()}
    result = []
    for index in sorted(selected):
        bank = dict(repo.headers[index].fields)["scriptsBank"].removesuffix("_bin")
        path = repo.root / "files/fielddata/script/scr_seq" / f"{bank}.s"
        result.extend(_instructions(path, repo.root, index, names))
    return result


def _instructions(path: Path, root: Path, header: int, names: dict[str, int]) -> list[dict]:
    lines = read_text(path).splitlines()
    if len(lines) > 30_000:
        raise ValueError(f"{path} : script HGSS trop long")
    label = ""
    result = []
    for number, line in enumerate(lines, 1):
        if re.fullmatch(r"\w+:", line):
            label = line[:-1]
        parts = line.strip().split(None, 1)
        if not parts or parts[0] not in _COMMANDS:
            continue
        args = [value.strip() for value in parts[1].split(",")]
        command = parts[0]
        if len(args) != (3 if command == "MoveWarp" else 5):
            raise ValueError(f"{path}:{number} : déplacement HGSS inconnu : {line}")
        record = dict(
            source=header,
            file=path.relative_to(root).as_posix(),
            line=number,
            label=label,
            command=command,
            arguments=args,
            access="Branche de scénario : consulter le script source",
        )
        if command in ("ScrCmd_722", "ScrCmd_723"):
            destination = int(args[2])
            if destination not in names.values():
                raise ValueError(f"{path}:{number} : destination de transport inconnue : {destination}")
            record.update(
                destination=destination,
                target_coordinates=[int(args[3]), int(args[4])],
                transport="train" if command == "ScrCmd_722" else "boat",
            )
        elif command != "MoveWarp" and args[0] in names:
            record["destination"] = names[args[0]]
        else:
            record["destination_kind"] = "modified_anchor" if command == "MoveWarp" else "variable"
        result.append(record)
    return result

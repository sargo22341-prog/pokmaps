"""Inventaire traçable des obtentions HGSS, séparé des probabilités sauvages."""

import re
import struct
from pathlib import Path
from types import MappingProxyType

from .pret_gen4_source import c_defines, read_text
from .pret_hgss_binary import read_archive

_COMMANDS = MappingProxyType(
    {
        "WildBattle": "fixed",
        "GiveMon": "gift",
        "GiveEgg": "egg",
        "GiveTogepiEgg": "egg",
        "GiveSpikyEarPichu": "event",
        "CreateRoamer": "roamer",
        "LoadNPCTrade": "trade",
        "GiveLoanMon": "loan",
        "ChooseStarter": "starter",
        "GiveDaycareEgg": "breeding",
    }
)
_SPECIAL_SPECIES = MappingProxyType(
    {"GiveTogepiEgg": (175,), "GiveSpikyEarPichu": (172,), "ChooseStarter": (152, 155, 158)}
)
_EXTERNAL = MappingProxyType({"D51R0201": "Arceus provenant d’ailleurs requis", "T03": "Mystécristal externe requis"})


def script_obtentions(root: Path) -> list[dict]:
    folder = root / "files/fielddata/script/scr_seq"
    paths = sorted(folder.glob("*.s"))
    if not 1 <= len(paths) <= 1200:
        raise ValueError("HGSS : nombre de scripts hors limite")
    species = c_defines(root / "include/constants/species.h", "SPECIES_")
    result = []
    for path in paths:
        text = read_text(path)
        label = ""
        records = []
        for line, raw in enumerate(text.splitlines(), 1):
            if re.fullmatch(r"\w+:", raw):
                label = raw[:-1]
            match = re.match(r"\s+(\w+)(?:\s+(.*))?$", raw)
            if match is None or match[1] not in _COMMANDS:
                continue
            command, arguments = match[1], (match[2] or "").split("//")[0].strip()
            location = path.stem.split("_", 3)[-1]
            external = _EXTERNAL.get(location) if command in ("WildBattle", "GiveMon") else None
            if command == "GiveSpikyEarPichu":
                external = "Pichu chromatique de distribution requis"
            transfer = command == "WildBattle" and "SPECIES_RAYQUAZA" in arguments
            if transfer:
                external = "Kyogre et Groudon de deux cartouches HGSS requis"
            records.append(
                {
                    "id": f"{path.stem}:{line}",
                    "source": path.relative_to(root).as_posix(),
                    "line": line,
                    "label": label,
                    "command": command,
                    "arguments": arguments,
                    "kind": _COMMANDS[command],
                    "native_location": location,
                    "species": _resolved_species(command, arguments, species, text),
                    "access": "external_transfer"
                    if transfer
                    else "external_event"
                    if external
                    else "local_conditional",
                    "ordinary_objective": external is None,
                    "exclusion_fr": external,
                }
            )
        if records:
            conditions = _native_conditions(text)
            for record in records:
                record["native_conditions"] = conditions
            result.extend(records)
    return result


def _native_conditions(text: str) -> list[str]:
    # Les branches restent ensemble : une ligne isolée ne prouve pas les conditions d'accès.
    pattern = (
        r"\s+(?:GoTo|Call|Compare|Check|SetVar|SetOrCopyVar|Get|SetFlag|ClearFlag|"
        r"FollowerPokeIsEventTrigger|ScrCmd_)\w*\b"
    )
    return [line.strip() for line in text.splitlines() if re.match(pattern, line) or re.fullmatch(r"\w+:", line)]


def _literal_species(command: str, arguments: str, species: dict[str, int]) -> list[int]:
    if command in _SPECIAL_SPECIES:
        return list(_SPECIAL_SPECIES[command])
    if command == "CreateRoamer":
        index = int(arguments)
        if index not in range(4):
            raise ValueError(f"HGSS : errant inconnu : {index}")
        return [(243, 244, 380, 381)[index]]
    if command not in ("WildBattle", "GiveMon", "GiveEgg"):
        return []
    first = arguments.split(",")[0]
    if first.startswith("SPECIES_"):
        return [species[first]]
    return []


def _resolved_species(command: str, arguments: str, species: dict[str, int], text: str) -> list[int]:
    direct = _literal_species(command, arguments, species)
    if direct or command not in ("WildBattle", "GiveMon"):
        return direct
    target = arguments.split(",")[0]
    if target == "VAR_UNK_407F" and "GetFossilPokemon" in text:
        return [138, 140, 142, 345, 347, 408, 410]
    values = re.findall(r"(?:SetVar|SetOrCopyVar) " + re.escape(target) + r", (\w+)", text)
    candidates = [species[v] if v.startswith("SPECIES_") else int(v) for v in values]
    if not candidates or any(not 1 <= n <= 493 for n in candidates):
        raise ValueError(f"HGSS : obtention variable sans candidats vérifiés : {command} {arguments}")
    return sorted(set(candidates))


def trade_catalog(root: Path) -> list[dict]:
    source = "files/a/1/1/2"
    members = read_archive(root / source)
    if len(members) != 13 or any(len(data) != 84 for data in members):
        raise ValueError("HGSS : treize échanges natifs de 84 octets attendus")
    records = []
    for index, data in enumerate(members):
        values = struct.unpack("<21I", data)
        given, requested = values[0], values[19]
        if not 1 <= given <= 493 or not 0 <= requested <= 493:
            raise ValueError(f"HGSS : espèces d'échange invalides : {index}")
        records.append(
            {
                "index": index,
                "source": source,
                "given": given,
                "requested": requested,
                "loan": index in (6, 7),
                "ordinary_objective": True,
            }
        )
    return records


def obtaining_catalog(root: Path) -> dict:
    courses = c_defines(root / "include/constants/pokewalker_courses.h", "WALKER_COURSE_")
    courses.pop("WALKER_COURSE_MAX", None)
    if sorted(courses.values()) != list(range(27)):
        raise ValueError("HGSS : vingt-sept parcours Pokéwalker attendus")
    return {
        "scripts": script_obtentions(root),
        "trades": trade_catalog(root),
        "pokewalker": {
            "courses": courses,
            "access": "accessory",
            "ordinary_objective": False,
            "source": "include/constants/pokewalker_courses.h",
            "map_headers": [],
            "exclusion_fr": "Accessoire Pokéwalker requis, y compris pour les parcours externes",
        },
        "distributions": {
            "access": "external_event",
            "ordinary_objective": False,
            "source": "src/scrcmd_mystery_gift.c",
            "exclusion_fr": "Distribution externe ; aucune disponibilité actuelle promise",
        },
        "transfers": {
            "access": "external_transfer",
            "ordinary_objective": False,
            "source": "src/scrcmd_c.c",
            "exclusion_fr": "Autre cartouche requise",
        },
        "objective_fr": "L’éligibilité locale concerne cette provenance seulement, sous ses conditions natives. "
        "Elle ne garantit ni une disponibilité immédiate ni la compatibilité de tous les choix de starters. "
        "Les événements, accessoires et transferts ne contribuent jamais par eux-mêmes à un objectif cartouche seule. "
        "Une espèce disposant aussi d’une provenance locale reste éligible par cette autre provenance.",
        "conditions_fr": "Les arguments variables et les branches natives sont conservés sans interprétation "
        "de sauvegarde. Les conditions brutes sont des preuves de source, pas des prédictions de disponibilité.",
    }

"""Lieux de Diamant/Perle décrits en C ou en assembleur : table des en-têtes, caméras et éclairages.

Le moteur du terrain de Diamant/Perle est surtout en assembleur : les tables y sont lues octet par octet, à
l'emplacement nommé ci-dessous, et leur forme est comparée par test à celle, décompilée, de Platine.
"""

from __future__ import annotations

import re
from itertools import pairwise
from pathlib import Path

from .pret_gen4_map_models import NO_ENCOUNTERS, CameraSettings, Gen4Header, Light, LightingPeriod
from .pret_gen4_source import ByteReader, c_defines, read_text

_HEADERS_FILE = "arm9/src/map_header.c"
_HEADER_LINE = re.compile(r"^\s*\{ (.*) \}, // (MAP_\w+)$")
_NARC = re.compile(r"^NARC_(\w+?)_narc_(\d{4})_bin$")
_ENCDATA = re.compile(r"^ENCDATA\((NARC_d_enc_data_narc_\d{4}_bin), (NARC_p_enc_data_narc_\d{4}_bin)\)$")
_HEADER_FIELD_COUNT = 19
# Table des réglages de caméra (CameraSettings, 24 octets chacun) dans les données de l'overlay du terrain.
_CAMERA_FILE = "arm9/overlays/05/asm/ov05_021DBD84.s"
_CAMERA_LABEL = "ov05_021F6608"
_CAMERA_SIZE = 24
# Table des fichiers d'éclairage (pointeurs vers « data/areaNNlight.txt ») de l'overlay du terrain.
_LIGHT_FILE = "arm9/overlays/05/asm/ov05_021DB44C.s"
_LIGHT_NAME = re.compile(r"^data/(area\d\dlight\.txt)$")
_LABEL = re.compile(r"^(\w+):")
_LIGHT_LINES = 9


def _archive(value: str, expected: str, where: str) -> int:
    match = _NARC.match(value)
    if match is None or match.group(1) != expected:
        raise ValueError(f"{where} : archive {expected} attendue : {value}")
    return int(match.group(2))


def _number(value: str, where: str) -> int:
    if value in {"TRUE", "FALSE"}:
        raise ValueError(f"{where} : nombre attendu : {value}")
    try:
        return int(value, 0)
    except ValueError as error:
        raise ValueError(f"{where} : nombre attendu : {value}") from error


def _split(body: str) -> list[str]:
    """Champs séparés par des virgules hors parenthèses (ENCDATA(diamant, perle) reste un seul champ)."""
    fields, depth, current = [], 0, []
    for char in body:
        depth += {"(": 1, ")": -1}.get(char, 0)
        if char == "," and depth == 0:
            fields.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    fields.append("".join(current).strip())
    return fields


def read_dp_headers(root: Path) -> dict[int, Gen4Header]:
    path = root / _HEADERS_FILE
    text = read_text(path)
    start = text.index("sMapHeaders[] = {")
    lines = [line for line in text[start : text.index("};", start)].splitlines()[1:] if line.strip()]
    # La table est positionnelle : son commentaire de fin de ligne est un ancien nom, maps.h fait foi.
    maps = c_defines(root / "include/constants/maps.h", "MAP_")
    names = {index: name for name, index in maps.items()}
    if len(names) != len(maps):
        raise ValueError(f"{root / 'include/constants/maps.h'} : numéros de lieux répétés")
    headers = {}
    for index, line in enumerate(lines):
        match = _HEADER_LINE.match(line)
        if match is None or index not in names:
            raise ValueError(f"{path} : ligne d'en-tête {index} illisible ou sans constante : {line.strip()[:80]}")
        headers[index] = _dp_header(index, names[index], _split(match.group(1)), f"{path} {names[index]}")
    if len(headers) != len(maps):
        raise ValueError(f"{path} : {len(headers)} en-têtes pour {len(maps)} constantes MAP_")
    return headers


def _dp_header(index: int, constant: str, fields: list[str], where: str) -> Gen4Header:
    if len(fields) != _HEADER_FIELD_COUNT:
        raise ValueError(f"{where} : {len(fields)} champs, {_HEADER_FIELD_COUNT} attendus")

    def flag(value: str) -> bool:
        if value not in {"TRUE", "FALSE"}:
            raise ValueError(f"{where} : booléen attendu : {value}")
        return value == "TRUE"

    # Quelques en-têtes écrivent la liste des PNJ préchargés en nombre plutôt qu'en nom d'archive.
    models = fields[1]
    return Gen4Header(
        index=index,
        constant=constant,
        area=_archive(fields[0], "area_data", where),
        move_models=_number(models, where) if models.isdigit() else _archive(models, "move_model_list", where),
        matrix=_archive(fields[2], "map_matrix", where),
        scripts=_archive(fields[3], "scr_seq_release", where),
        init_scripts=_archive(fields[4], "scr_seq_release", where),
        texts=_archive(fields[5], "msg", where),
        day_music=fields[6],
        night_music=fields[7],
        encounters=_encounters(fields[8], where),
        events=_archive(fields[9], "zone_event_release", where),
        location=fields[10].removeprefix("MAPSEC_"),
        weather=_number(fields[11], where),
        camera=_number(fields[12], where),
        map_type=_number(fields[13], where),
        battle_background=_number(fields[14], where),
        bike=flag(fields[15]),
        running=flag(fields[16]),
        escape_rope=flag(fields[17]),
        fly=flag(fields[18]),
    )


def _encounters(value: str, where: str) -> tuple[tuple[str, int], ...]:
    if value.startswith("0x") and int(value, 16) == NO_ENCOUNTERS:
        return ()
    match = _ENCDATA.match(value)
    if match is None:
        raise ValueError(f"{where} : tables de rencontres illisibles : {value}")
    return (
        ("diamond", _archive(match.group(1), "d_enc_data", where)),
        ("pearl", _archive(match.group(2), "p_enc_data", where)),
    )


def _labelled_bytes(path: Path, label: str) -> bytes:
    """Octets `.byte` qui suivent `label:` jusqu'à une ligne vide, un label ou une section."""
    lines = read_text(path).splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.startswith(f"{label}:"))
    except StopIteration as error:
        raise ValueError(f"{path} : label {label} absent") from error
    data = bytearray()
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if not stripped.startswith(".byte"):
            if not stripped or _LABEL.match(stripped) or stripped.startswith((".section", ".global")):
                break
            raise ValueError(f"{path} : directive inattendue dans {label} : {stripped}")
        data.extend(int(value, 16) for value in stripped.removeprefix(".byte").split(","))
    return bytes(data)


def read_dp_cameras(root: Path) -> tuple[CameraSettings, ...]:
    path = root / _CAMERA_FILE
    data = _labelled_bytes(path, _CAMERA_LABEL)
    if not data or len(data) % _CAMERA_SIZE:
        raise ValueError(f"{path} : table des caméras de {len(data)} octets")
    reader = ByteReader(data, f"{path} {_CAMERA_LABEL}")
    cameras = []
    for offset in range(0, len(data), _CAMERA_SIZE):
        distance, angle_x, angle_y, angle_z, padding, projection, unused, fov = reader.unpack("iHHHHBBH", offset)
        near, far = reader.unpack("ii", offset + 16)
        if angle_y or angle_z or padding or unused or projection > 1:
            raise ValueError(f"{path} : caméra {offset // _CAMERA_SIZE} inattendue")
        cameras.append(CameraSettings(distance, angle_x, projection, fov, near, far))
    return tuple(cameras)


def read_dp_lighting(root: Path) -> dict[int, tuple[LightingPeriod, ...]]:
    names = _light_files(root / _LIGHT_FILE)
    return {index: read_light_file(root / "files/data" / name) for index, name in enumerate(names)}


def _light_files(path: Path) -> tuple[str, ...]:
    """Noms des fichiers d'éclairage, dans l'ordre de la table de pointeurs du moteur."""
    lines = [line.strip() for line in read_text(path).splitlines()]
    strings = {}
    for previous, line in pairwise(lines):
        label = _LABEL.match(previous)
        if label and line.startswith(".asciz "):
            strings[label.group(1)] = line.removeprefix(".asciz ").strip('"')
    tables = []
    for line in lines:
        if line.startswith(".word "):
            labels = [value.strip() for value in line.removeprefix(".word ").split(",")]
            names = [_LIGHT_NAME.match(strings.get(label, "")) for label in labels]
            if all(names):
                tables.append(tuple(name.group(1) for name in names if name))
    if len(tables) != 1:
        raise ValueError(f"{path} : {len(tables)} tables de fichiers d'éclairage, une attendue")
    return tables[0]


def read_light_file(path: Path) -> tuple[LightingPeriod, ...]:
    """Format texte lu par AreaLightTemplate_New : heure de fin, quatre lumières, quatre couleurs, ligne vide."""
    lines = read_text(path).replace("\r\n", "\n").split("\n")
    if lines[-1] == "":
        lines.pop()
    if lines[-1] != "EOF" or (len(lines) - 1) % (_LIGHT_LINES + 1):
        raise ValueError(f"{path} : fichier d'éclairage mal terminé")
    periods = []
    for start in range(0, len(lines) - 1, _LIGHT_LINES + 1):
        rows = [_csv_ints(line, path) for line in lines[start : start + _LIGHT_LINES]]
        if lines[start + _LIGHT_LINES] != "" or len(rows[0]) != 1 or any(len(r) != 7 for r in rows[1:5]):
            raise ValueError(f"{path} : période d'éclairage {len(periods)} illisible")
        lights = tuple(Light(bool(r[0]), (r[1], r[2], r[3]), (r[4], r[5], r[6])) for r in rows[1:5])
        colors = [(r[0], r[1], r[2]) for r in rows[5:9] if len(r) == 3]
        if len(colors) != 4:
            raise ValueError(f"{path} : couleurs d'éclairage illisibles")
        periods.append(LightingPeriod(rows[0][0], lights, *colors))
    ends = [period.end_time for period in periods]
    if not periods or ends != sorted(set(ends)) or ends[-1] > 43_200:
        raise ValueError(f"{path} : heures de fin d'éclairage invalides : {ends}")
    return tuple(periods)


def _csv_ints(line: str, path: Path) -> list[int]:
    if not line.endswith(","):
        raise ValueError(f"{path} : ligne d'éclairage sans virgule finale : {line}")
    try:
        return [int(value) for value in line[:-1].split(",")]
    except ValueError as error:
        raise ValueError(f"{path} : ligne d'éclairage illisible : {line}") from error

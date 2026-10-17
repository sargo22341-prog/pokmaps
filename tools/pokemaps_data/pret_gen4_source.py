"""Lectures bornées communes aux deux désassemblages DS : JSON, binaires extraits et constantes C ou metang."""

from __future__ import annotations

import json
import re
import struct
from pathlib import Path

_MAX_JSON_BYTES = 4 * 1024 * 1024
_MAX_TEXT_BYTES = 8 * 1024 * 1024
# Le plus gros fichier binaire lu (modèle 3D d'un bloc de terrain) pèse moins de 200 Kio.
MAX_BINARY_BYTES = 4 * 1024 * 1024
_ENUM_LINE = re.compile(r"^(\w+)(?:\s*=\s*(\w+))?$")
_DEFINE = re.compile(r"^\s*#define\s+(\w+)[ \t]+([^\n/]+)", re.MULTILINE)
_TERM = re.compile(r"\s*([+-]?)\s*(\w+)")
_C_ENUM = re.compile(r"enum\s+(\w+)\s*\{(.*?)\}", re.DOTALL)
_C_COMMENT = re.compile(r"//[^\n]*|/\*.*?\*/", re.DOTALL)
_INCLUDE = re.compile(r'^\s*#include\s+"(constants/[\w/]+\.h)"', re.MULTILINE)
_INTEGER_DEFINE = re.compile(r"^\s*#define\s+(\w+)[ \t]+(-?(?:0x[0-9A-Fa-f]+|\d+))[ \t]*(?://[^\n]*)?$", re.MULTILINE)
_MAX_INCLUDES = 256


def read_json(path: Path) -> dict:
    """Objet JSON d'un dépôt DS, borné en taille."""
    if path.stat().st_size > _MAX_JSON_BYTES:
        raise ValueError(f"{path} : JSON DS trop volumineux")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} : objet JSON attendu")
    return value


def read_json_list(path: Path) -> list:
    """Liste JSON d'un dépôt DS (éclairages), bornée en taille."""
    if path.stat().st_size > _MAX_JSON_BYTES:
        raise ValueError(f"{path} : JSON DS trop volumineux")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError(f"{path} : liste JSON attendue")
    return value


def read_text(path: Path) -> str:
    """Source texte d'un dépôt DS, bornée en taille."""
    if path.stat().st_size > _MAX_TEXT_BYTES:
        raise ValueError(f"{path} : source DS trop volumineuse")
    return path.read_text(encoding="utf-8")


def read_binary(path: Path, max_bytes: int = MAX_BINARY_BYTES) -> bytes:
    """Fichier binaire extrait d'un dépôt DS, borné en taille."""
    size = path.stat().st_size
    if size > max_bytes:
        raise ValueError(f"{path} : {size} octets, au plus {max_bytes} attendus")
    return path.read_bytes()


class ByteReader:
    """Lecture petit-boutiste d'un tampon : toute lecture hors des bornes arrête avec le nom du fichier."""

    def __init__(self, data: bytes, where: str) -> None:
        self.data = data
        self.where = where

    def require(self, offset: int, size: int) -> None:
        if offset < 0 or size < 0 or offset + size > len(self.data):
            raise ValueError(
                f"{self.where} : lecture de {size} octets à {offset:#x} hors du fichier ({len(self.data)})"
            )

    def unpack(self, fmt: str, offset: int) -> tuple:
        self.require(offset, struct.calcsize("<" + fmt))
        return struct.unpack_from("<" + fmt, self.data, offset)

    def u8(self, offset: int) -> int:
        return self.unpack("B", offset)[0]

    def u16(self, offset: int) -> int:
        return self.unpack("H", offset)[0]

    def s16(self, offset: int) -> int:
        return self.unpack("h", offset)[0]

    def u32(self, offset: int) -> int:
        return self.unpack("I", offset)[0]

    def s32(self, offset: int) -> int:
        return self.unpack("i", offset)[0]

    def slice(self, offset: int, size: int) -> bytes:
        self.require(offset, size)
        return self.data[offset : offset + size]


def metang_enum(path: Path) -> dict[str, int]:
    """Constantes d'une énumération metang de Platine (generated/*.txt) : une par ligne, « NOM = AUTRE » pour un
    alias ou une valeur explicite, la suivante prenant la valeur + 1."""
    values: dict[str, int] = {}
    following = 0
    for number, line in enumerate(read_text(path).splitlines(), start=1):
        if not (line := line.strip()):
            continue
        match = _ENUM_LINE.match(line)
        if match is None:
            raise ValueError(f"{path}:{number} : ligne d'énumération illisible : {line}")
        name, value = match.groups()
        if value is not None:
            following = values[value] if value in values else _integer(value, f"{path}:{number}")
        if name in values:
            raise ValueError(f"{path}:{number} : constante répétée : {name}")
        values[name] = following
        following += 1
    return values


def c_enum(path: Path, name: str) -> dict[str, int]:
    """Membres de l'énumération C `name` (valeurs implicites ou entières explicites)."""
    text = _C_COMMENT.sub("", read_text(path))
    for match in _C_ENUM.finditer(text):
        if match.group(1) != name:
            continue
        values: dict[str, int] = {}
        following = 0
        for member in (part.strip() for part in match.group(2).split(",")):
            if not member:
                continue
            key, _, value = (piece.strip() for piece in member.partition("="))
            if value:
                following = values[value] if value in values else _integer(value, f"{path} {name}")
            values[key] = following
            following += 1
        return values
    raise ValueError(f"{path} : énumération {name} absente")


def c_defines(path: Path, prefix: str) -> dict[str, int]:
    """Constantes `#define PREFIXE… valeur` d'un en-tête C : entier, ou somme et différence d'entiers et de
    constantes déjà définies, entre parenthèses ou non."""
    values: dict[str, int] = {}
    for name, expression in _DEFINE.findall(read_text(path)):
        if name.startswith(prefix):
            values[name] = _sum(expression.strip().removeprefix("(").removesuffix(")"), values, f"{path} {name}")
    if not values:
        raise ValueError(f"{path} : aucune constante {prefix}")
    return values


def included_defines(root: Path, sources: tuple[str, ...]) -> dict[str, int]:
    """Constantes `#define NOM entier` des en-têtes include/constants/ inclus, directement ou non, par les fichiers
    `sources` du dépôt, puis membres de leurs énumérations C (valeurs implicites, entières ou déjà connues) ; une
    constante définie deux fois avec deux valeurs différentes est écartée."""
    values: dict[str, int] = {}
    conflicts: set[str] = set()
    texts = _included_texts(root, sources)
    found = [(name, int(value, 0)) for text in texts for name, value in _INTEGER_DEFINE.findall(text)]
    defines = dict(found)
    for text in texts:
        found += _enum_members(_C_COMMENT.sub("", text), defines)
    for name, number in found:
        if values.get(name, number) != number:
            conflicts.add(name)
        values[name] = number
    return {name: value for name, value in values.items() if name not in conflicts}


def _included_texts(root: Path, sources: tuple[str, ...]) -> list[str]:
    texts = []
    pending = [root / source for source in sources]
    seen: set[Path] = set()
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        if len(seen) > _MAX_INCLUDES:
            raise ValueError(f"{root} : trop d'en-têtes inclus depuis {sources}")
        text = read_text(path)
        pending += [root / "include" / name for name in _INCLUDE.findall(text)]
        texts.append(text)
    return texts


def _enum_members(text: str, known: dict[str, int]) -> list[tuple[str, int]]:
    """Membres des énumérations C du texte ; une énumération dont une valeur explicite reste inconnue est écartée."""
    result = []
    for match in _C_ENUM.finditer(text):
        members: dict[str, int] = {}
        following = 0
        for member in (part.strip() for part in match.group(2).split(",")):
            if not member:
                continue
            key, _, value = (piece.strip() for piece in member.partition("="))
            if value:
                resolved = members.get(value, known.get(value))
                if resolved is None and not re.fullmatch(r"-?(?:0x[0-9A-Fa-f]+|\d+)", value):
                    members = {}
                    break
                following = resolved if resolved is not None else int(value, 0)
            members[key] = following
            following += 1
        result += members.items()
    return result


def _sum(expression: str, known: dict[str, int], where: str) -> int:
    total, position = 0, 0
    for match in _TERM.finditer(expression):
        if match.start() != position or (position and not match.group(1)):
            raise ValueError(f"{where} : expression non prise en charge : {expression}")
        term = match.group(2)
        value = known[term] if term in known else _integer(term, where)
        total += -value if match.group(1) == "-" else value
        position = match.end()
    if position != len(expression.rstrip()) or not position:
        raise ValueError(f"{where} : expression non prise en charge : {expression}")
    return total


def _integer(value: str, where: str) -> int:
    try:
        return int(value, 0)
    except ValueError as error:
        raise ValueError(f"{where} : valeur entière attendue : {value}") from error

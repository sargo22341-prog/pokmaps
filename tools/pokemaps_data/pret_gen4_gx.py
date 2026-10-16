"""Listes d'affichage GX des formes Nitro, décodées en primitives (triangles, quadrilatères et bandes).

Les commandes sont empaquetées par quatre opcodes sur un mot, suivis de leurs paramètres (GXFifo du Nitro
SDK). Seules les commandes rencontrées dans les modèles des deux dépôts sont acceptées ; une autre arrête la
lecture avec son décalage.
"""

from __future__ import annotations

from dataclasses import dataclass

from .pret_gen4_source import ByteReader

# Nombre de mots de paramètres des commandes acceptées.
_PARAMETERS = {
    0x00: 0,  # NOP
    0x14: 1,  # MTX_RESTORE : matrice de nœud courante
    0x1B: 3,  # MTX_SCALE
    0x20: 1,  # COLOR
    0x21: 1,  # NORMAL
    0x22: 1,  # TEXCOORD
    0x23: 2,  # VTX_16
    0x24: 1,  # VTX_10
    0x25: 1,  # VTX_XY
    0x26: 1,  # VTX_XZ
    0x27: 1,  # VTX_YZ
    0x28: 1,  # VTX_DIFF
    0x40: 1,  # BEGIN_VTXS
    0x41: 0,  # END_VTXS
}
TRIANGLES, QUADS, TRIANGLE_STRIP, QUAD_STRIP = 0, 1, 2, 3
_MAX_VERTICES = 65536


@dataclass(frozen=True)
class Vertex:
    position: tuple[int, int, int]  # fx16 du modèle, avant l'échelle de position
    texcoord: tuple[int, int]  # pas de 1/16 de texel
    color: tuple[int, int, int] | None
    normal: tuple[int, int, int] | None  # fx10 (512 = 1,0)
    matrix: int


@dataclass(frozen=True)
class Primitive:
    kind: int
    vertices: tuple[Vertex, ...]


@dataclass
class _State:
    position: tuple[int, int, int] = (0, 0, 0)
    texcoord: tuple[int, int] = (0, 0)
    color: tuple[int, int, int] | None = None
    normal: tuple[int, int, int] | None = None
    matrix: int = 0


def signed(value: int, bits: int) -> int:
    value &= (1 << bits) - 1
    return value - (1 << bits) if value >> (bits - 1) else value


def commands(data: bytes, where: str) -> list[tuple[int, tuple[int, ...]]]:
    """(opcode, paramètres) dans l'ordre ; les NOP de remplissage sont omis."""
    reader = ByteReader(data, where)
    if len(data) % 4:
        raise ValueError(f"{where} : liste d'affichage non alignée")
    result = []
    position = 0
    while position < len(data):
        opcodes = reader.slice(position, 4)
        position += 4
        for opcode in opcodes:
            if opcode not in _PARAMETERS:
                raise ValueError(f"{where} : commande GX inconnue {opcode:#x} avant {position:#x}")
            count = _PARAMETERS[opcode]
            parameters = reader.unpack(f"{count}I", position)
            position += 4 * count
            if opcode:
                result.append((opcode, parameters))
    return result


def primitives(data: bytes, where: str) -> tuple[Primitive, ...]:
    state = _State()
    result: list[Primitive] = []
    kind: int | None = None
    vertices: list[Vertex] = []
    for opcode, parameters in commands(data, where):
        if opcode == 0x40:
            if kind is not None:
                raise ValueError(f"{where} : BEGIN_VTXS imbriqué")
            kind, vertices = parameters[0] & 3, []
        elif opcode == 0x41:
            if kind is None:
                raise ValueError(f"{where} : END_VTXS sans BEGIN_VTXS")
            result.append(_primitive(kind, vertices, where))
            kind = None
        elif opcode >= 0x23:
            if kind is None:
                raise ValueError(f"{where} : sommet hors de BEGIN_VTXS")
            state.position = _position(opcode, parameters, state.position)
            vertices.append(Vertex(state.position, state.texcoord, state.color, state.normal, state.matrix))
            if len(vertices) > _MAX_VERTICES:
                raise ValueError(f"{where} : primitive de plus de {_MAX_VERTICES} sommets")
        else:
            _attribute(state, opcode, parameters, where)
    # Une liste peut finir sans END_VTXS : la primitive ouverte est close par la fin de la liste.
    if kind is not None:
        result.append(_primitive(kind, vertices, where))
    return tuple(result)


def _attribute(state: _State, opcode: int, parameters: tuple[int, ...], where: str) -> None:
    value = parameters[0]
    if opcode == 0x14:
        state.matrix = value & 0x1F
    elif opcode == 0x20:
        state.color = (value & 31, (value >> 5) & 31, (value >> 10) & 31)
    elif opcode == 0x21:
        state.normal = (signed(value, 10), signed(value >> 10, 10), signed(value >> 20, 10))
    elif opcode == 0x22:
        state.texcoord = (signed(value, 16), signed(value >> 16, 16))
    elif opcode == 0x1B:
        raise ValueError(f"{where} : MTX_SCALE dans une forme, non pris en charge")


def _position(opcode: int, parameters: tuple[int, ...], current: tuple[int, int, int]) -> tuple[int, int, int]:
    x, y, z = current
    value = parameters[0]
    if opcode == 0x23:
        return signed(value, 16), signed(value >> 16, 16), signed(parameters[1], 16)
    if opcode == 0x24:
        return signed(value, 10) << 6, signed(value >> 10, 10) << 6, signed(value >> 20, 10) << 6
    if opcode == 0x25:
        return signed(value, 16), signed(value >> 16, 16), z
    if opcode == 0x26:
        return signed(value, 16), y, signed(value >> 16, 16)
    if opcode == 0x27:
        return x, signed(value, 16), signed(value >> 16, 16)
    return x + signed(value, 10), y + signed(value >> 10, 10), z + signed(value >> 20, 10)


def _primitive(kind: int, vertices: list[Vertex], where: str) -> Primitive:
    minimum, step = {TRIANGLES: (3, 3), QUADS: (4, 4), TRIANGLE_STRIP: (3, 1), QUAD_STRIP: (4, 2)}[kind]
    if len(vertices) < minimum or (len(vertices) - minimum) % step:
        raise ValueError(f"{where} : {len(vertices)} sommets pour une primitive de type {kind}")
    return Primitive(kind, tuple(vertices))


def triangles(primitive: Primitive) -> list[tuple[Vertex, Vertex, Vertex]]:
    """Triangles d'une primitive, dans le sens de rotation du matériel."""
    v = primitive.vertices
    if primitive.kind == TRIANGLES:
        return [(v[i], v[i + 1], v[i + 2]) for i in range(0, len(v), 3)]
    if primitive.kind == QUADS:
        return [t for i in range(0, len(v), 4) for t in ((v[i], v[i + 1], v[i + 2]), (v[i], v[i + 2], v[i + 3]))]
    if primitive.kind == TRIANGLE_STRIP:
        return [(v[i], v[i + 1], v[i + 2]) if i % 2 == 0 else (v[i + 1], v[i], v[i + 2]) for i in range(len(v) - 2)]
    return [t for i in range(0, len(v) - 2, 2) for t in ((v[i], v[i + 1], v[i + 3]), (v[i], v[i + 3], v[i + 2]))]

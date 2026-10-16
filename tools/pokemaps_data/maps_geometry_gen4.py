"""Transformations des nœuds Nitro et pile de matrices SBC pour les cartes DS."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from .pret_gen4_nitro import FX_ONE, NitroModel, NitroNode

Vector = tuple[int, int, int]
_IDENTITY = (FX_ONE, 0, 0, 0, FX_ONE, 0, 0, 0, FX_ONE)


@dataclass(frozen=True)
class Transform:
    rotation: tuple[int, ...] = _IDENTITY
    translation: Vector = (0, 0, 0)

    def point(self, point: Vector) -> Vector:
        return tuple(
            sum(point[i] * self.rotation[i * 3 + k] for i in range(3)) // FX_ONE + self.translation[k] for k in range(3)
        )

    def then(self, parent: Transform) -> Transform:
        rotation = tuple(
            sum(self.rotation[row * 3 + i] * parent.rotation[i * 3 + column] for i in range(3)) // FX_ONE
            for row in range(3)
            for column in range(3)
        )
        return Transform(rotation, parent.point(self.translation))


def node_transform(node: NitroNode) -> Transform:
    rotation = tuple(node.rotation[i] * node.scale[i // 3] // FX_ONE for i in range(9))
    return Transform(rotation, node.translation)


@dataclass(frozen=True)
class ShapeDraw:
    material: int
    shape: int
    transform: Transform
    stack: tuple[tuple[int, Transform], ...]
    position_scale: int


def shape_draws(model: NitroModel) -> Iterator[ShapeDraw]:
    current = Transform()
    stack: dict[int, Transform] = {}
    material, scale, visible = 0, FX_ONE, True
    for command in model.render:
        opcode, flags, args = command.opcode, command.flags, command.arguments
        if opcode == 1:
            return
        if opcode == 6:
            current = _node(model, args, flags, current, stack)
        elif opcode == 3:
            current = _restore(stack, args[0], model.name)
        elif opcode == 4:
            material = args[0]
        elif opcode == 2:
            visible = bool(args[1])
        elif opcode == 11:
            scale = model.inverse_position_scale if flags else model.position_scale
        elif opcode == 5 and visible:
            if material >= len(model.materials) or args[0] >= len(model.shapes):
                raise ValueError(f"{model.name} : matériau ou forme hors limites")
            yield ShapeDraw(material, args[0], current, tuple(sorted(stack.items())), scale)
        elif opcode not in (0, 2, 4, 5):
            raise ValueError(f"{model.name} : commande de rendu SBC non gérée : {opcode:#x}, drapeaux {flags}")


def _restore(stack: dict[int, Transform], index: int, name: str) -> Transform:
    if index not in stack:
        raise ValueError(f"{name} : matrice {index} non initialisée")
    return stack[index]


def _node(
    model: NitroModel, args: tuple[int, ...], flags: int, current: Transform, stack: dict[int, Transform]
) -> Transform:
    index = args[0]
    if index >= len(model.nodes):
        raise ValueError(f"{model.name} : nœud {index} absent")
    position = 3
    destination = args[position] if flags & 1 else None
    position += bool(flags & 1)
    if flags & 2:
        current = _restore(stack, args[position], model.name)
    current = node_transform(model.nodes[index]).then(current)
    if destination is not None:
        stack[destination] = current
    return current

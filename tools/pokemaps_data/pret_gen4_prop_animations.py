"""Associations modèle → animations automatiques des deux moteurs DS."""

from __future__ import annotations

from functools import cached_property
from pathlib import Path

from .pret_gen4 import Gen4PretRepo
from .pret_gen4_animation import animation_first_frame, narc_members
from .pret_gen4_narc import members
from .pret_gen4_nitro import NitroFile
from .pret_gen4_source import ByteReader, read_binary


class PropAnimations:
    def __init__(self, repo: Gen4PretRepo) -> None:
        self.repo = repo

    @cached_property
    def _records(self) -> tuple[bytes, ...]:
        if self.repo.platinum:
            path = self.repo.root / "res/prebuilt/arc/bm_anime_list.narc"
            return narc_members(read_binary(path), str(path))
        files = members(self.repo.root / "files/arc/bm_anime_list")
        if set(files) != set(range(len(files))):
            raise ValueError(f"{self.repo.root} : table d'animations non contiguë")
        return tuple(read_binary(files[index]) for index in range(len(files)))

    @cached_property
    def _files(self) -> dict[int, Path]:
        if self.repo.platinum:
            folder = self.repo.root / "res/field/props/animations"
            return {
                index: folder / name
                for name, index in self.repo.names.order("res/field/props/animations/prop_animations.order").items()
            }
        return members(self.repo.root / "files/arc/bm_anime")

    def first_frame(self, index: int, file: NitroFile) -> NitroFile:
        if index >= len(self._records):
            return file
        record = self._records[index]
        reader = ByteReader(record, f"{self.repo.variant} animations du modèle {index}")
        if len(record) != 20:
            raise ValueError(f"{reader.where} : enregistrement d'animations de taille incorrecte")
        # Les deux bits diffèrent chargement et ajout au modèle jusqu'à une action de scénario.
        if reader.u8(1) & 3:
            return file
        for animation in reader.unpack("4i", 4):
            if animation == -1:
                break
            if animation not in self._files:
                raise ValueError(f"{reader.where} : animation {animation} absente")
            path = self._files[animation]
            file = animation_first_frame(file, read_binary(path), str(path))
        return file

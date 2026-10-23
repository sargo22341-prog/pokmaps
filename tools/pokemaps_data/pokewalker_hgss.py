"""Les vingt-sept parcours de l'accessoire, table native de 192 octets par entrée."""

import re
import struct
from pathlib import Path

from .pret_gen4_source import c_defines, read_text


def walker_catalog(root: Path) -> dict:
    source = "asm/overlay_112.s"
    text = read_text(root / source)
    body = text.split("\nov112_021F4138:", 1)[1].split("\nov112_021F5578:", 1)[0]
    data = bytes(
        int(v, 16) for line in body.splitlines() if ".byte" in line for v in re.findall(r"0x([\da-fA-F]{2})", line)
    )
    if len(data) != 27 * 192:
        raise ValueError("HGSS : vingt-sept parcours Pokéwalker de 192 octets attendus")
    names = c_defines(root / "include/constants/pokewalker_courses.h", "WALKER_COURSE_")
    names.pop("WALKER_COURSE_MAX")
    rows = []
    for name, index in sorted(names.items(), key=lambda row: row[1]):
        entry = data[index * 192 : (index + 1) * 192]
        mons = [_walker_mon(entry[8 + i * 20 : 28 + i * 20], i) for i in range(6)]
        items = [
            dict(zip(("item", "steps", "weight"), struct.unpack_from("<3H", entry, 128 + i * 6), strict=True))
            for i in range(10)
        ]
        rows.append(
            dict(
                index=index,
                native_name=name,
                watts=struct.unpack_from("<I", entry)[0],
                national=8 <= index < 20,
                access="accessory" if index < 20 else "external_accessory",
                initially_unlocked=index < 2,
                pokemon=mons,
                items=items,
                native_tail=list(entry[188:192]),
                ordinary_objective=False,
            )
        )
    return dict(
        source=source,
        table="ov112_021F4138",
        unlock_function="ov112_021E95A0",
        courses=rows,
        rule_fr="Les vingt premiers parcours utilisent les Watts cumulés ; à partir du neuvième, le National "
        "est requis. Les deux premiers sont ouverts au départ. Les sept autres ont un accès externe spécifique. "
        "Les groupes A, B et C proposent chacun deux candidats ; poids et seuils de pas sont conditionnels. "
        "Aucun taux global ni tirage n’est prédit. Tous les parcours exigent l’accessoire et sont exclus "
        "des objectifs cartouche seule.",
    )


def _walker_mon(data: bytes, index: int) -> dict:
    species, level, item = struct.unpack_from("<3H", data)
    if not 1 <= species <= 493 or not 1 <= level <= 100:
        raise ValueError(f"HGSS : Pokémon Pokéwalker invalide : {species}/{level}")
    return dict(
        group=("A", "B", "C")[index // 2],
        candidate=index % 2,
        species=species,
        level=level,
        item=item,
        native_flags=list(data[6:8]),
        moves=list(struct.unpack_from("<4H", data, 8)),
        steps=struct.unpack_from("<H", data, 16)[0],
        weight=struct.unpack_from("<H", data, 18)[0],
    )

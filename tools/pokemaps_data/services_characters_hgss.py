"""Services persistants HGSS : étapes, quantités et monnaies du moteur natif."""

import re
from pathlib import Path

from .pret_gen4_source import read_text
from .pret_hgss_flow_context import read_constants


def service_catalog(root: Path) -> dict:
    constants = read_constants(root)
    source = "src/mom_gift.c"
    text = read_text(root / source)
    normal = [
        dict(item=constants[item], threshold=int(threshold), cost=int(cost), quantity=1)
        for item, threshold, cost in re.findall(r"\{\s*(ITEM_\w+),\s*(\d+),\s*(\d+)\s*\}", text)
    ]
    berries = [
        dict(item=constants[item], quantity=int(quantity), cost=int(cost))
        for item, quantity, cost in re.findall(r"\{\s*(ITEM_\w+) - ITEM_CHERI_BERRY,\s*(\d+),\s*(\d+)\s*\}", text)
    ]
    fossils = [
        dict(item=constants[item], species=constants[species], quantity=1, level=20)
        for item, species in re.findall(
            r"\{\s*(ITEM_\w+),\s*(SPECIES_\w+)\s*\}", read_text(root / "src/scrcmd_fossils.c")
        )
    ]
    if (len(normal), len(berries), len(fossils)) != (9, 17, 7):
        raise ValueError("HGSS : cadeaux de la mère ou fossiles incomplets")
    return dict(
        mother=dict(
            normal=normal,
            berries=berries,
            source=source,
            queue_capacity=5,
            steps_fr=[
                "Épargne activée",
                "Achats normaux non déjà reçus, dans l'ordre des seuils",
                "Sinon, franchissement d'un palier de 3 000 pour un lot aléatoire de Baies",
                "Coût débité de l'épargne",
                "File de cinq achats, retrait en boutique dans l'ordre",
            ],
            delivery_source="src/save_pokegear.c",
        ),
        fossils=dict(
            offers=fossils,
            source="src/scrcmd_fossils.c",
            bank=755,
            steps_fr=[
                "Déposer un fossile",
                "Sortir du bâtiment puis revenir",
                "Prévoir une place dans l'équipe",
                "Retirer le Pokémon de niveau 20",
            ],
            delay="leave_and_reenter",
            variable=0x407F,
        ),
        **_other_services(root, constants),
    )


def _other_services(root: Path, constants: dict[str, int]) -> dict:
    return dict(
        daycare=dict(
            capacity=2,
            currency="money",
            cost_formula="100 * (levels_gained + 1)",
            source="src/get_egg.c",
            steps_fr=["Confier un Pokémon", "Payer au retrait"],
        ),
        relearner=dict(
            item=constants["ITEM_HEART_SCALE"],
            quantity=1,
            bank=948,
            payment="after_success",
            source="files/fielddata/script/scr_seq/scr_seq_0948_T30R0601.s",
        ),
        scratch_cards=dict(
            currency="battle_points",
            cost=1,
            cards=3,
            bank=263,
            source="files/fielddata/script/scr_seq/scr_seq_0263.s",
            reward_source="asm/overlay_87.s",
            outcome="native_minigame_result",
            rewards=_scratch_rewards(root),
            steps_fr=[
                "Payer 1 Point Combat",
                "Jouer les trois cartes",
                "Retirer les lots gagnés ; place requise dans le Sac",
            ],
        ),
        mystery_gift=dict(
            availability="external_event",
            source="src/field/scrcmd_pokemon_misc.c",
            description_fr="Livraison conditionnée à un événement externe déjà enregistré",
        ),
    )


def _scratch_rewards(root: Path) -> list[dict]:
    text = read_text(root / "asm/overlay_87.s")
    body = text.split("ov87_021E8358:", 1)[1].split("ov87_021E8388:", 1)[0]
    data = bytes(
        int(value, 16)
        for line in body.splitlines()
        if line.strip().startswith(".byte")
        for value in re.findall(r"0x([\da-fA-F]{2})", line)
    )
    items = [int.from_bytes(data[i : i + 2], "little") for i in range(0, len(data), 2)]
    if len(items) != 24 or items[-1] != 0:
        raise ValueError("HGSS : lots des cartes à gratter illisibles")
    return [dict(item=item, quantity=3) for item in items[:-1]] + [dict(item=92, quantity=1)]


def standard_services(actors: list[dict]) -> None:
    names = {
        "std_apricorn_tree": "Arbre à Noigrumes",
        "std_daycare_man": "Pension",
        "std_daycare_lady": "Pension",
        "std_moms_gift_deliveryman": "Achats de la mère",
        "std_mystery_gift_deliveryman": "Livraison de Cadeau Mystère",
        "std_scratch_card": "Cartes à gratter",
    }
    for actor in actors:
        script = actor["native"]["script"]
        if script in names:
            actor.update(useful=True, name_fr=names[script], standard_service=script)


def daycare_price(levels_gained: int) -> int:
    if not 0 <= levels_gained <= 99:
        raise ValueError("HGSS : progression de Pension hors limites")
    return 100 * (levels_gained + 1)

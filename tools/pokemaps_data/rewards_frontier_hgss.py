"""Points de la Tour et lots du comptoir, lus dans les scripts HGSS."""

import re
from pathlib import Path

from .pret_gen4_engine_text import c_initializer
from .pret_gen4_source import read_text


def reward_catalog(root: Path) -> dict:
    source = "src/unk_0204A3F4.c"
    text = read_text(root / source)
    tables = {
        key: [int(n) for n in re.findall(r"\d+", c_initializer(text, name, source))]
        for key, name in (
            ("ordinary", "RegularBattlePointRewards"),
            ("link", "LinkBattlePointRewards"),
            ("wifi_historical", "WifiBattlePointRewards"),
        )
    }
    if [len(v) for v in tables.values()] != [8, 8, 12] or "battlePoints = 20;" not in text:
        raise ValueError("HGSS : récompenses de la Tour illisibles")
    script = "files/fielddata/script/scr_seq/scr_seq_0076_D32.s"
    text = read_text(root / script)
    pattern = (
        r"^(\w+):\s+SetVar VAR_SPECIAL_x8004, (\d+)\s+SetVar VAR_SPECIAL_x8005, (\d+)"
        r"\s+SetVar VAR_SPECIAL_x8006, (\d+)\s+(?:SetVar VAR_SPECIAL_x8001, (\d+)\s+)?GoTo (\w+)"
    )
    offers = []
    for label, item, space, cost, move, target in re.findall(pattern, text, re.MULTILINE):
        if target not in ("_09F3", "_0F40"):
            raise ValueError(f"HGSS : remise de lot inconnue : {target}")
        offers.append(
            dict(
                label=label,
                item=int(item),
                quantity=1,
                required_bag_space=int(space),
                cost=int(cost),
                currency="battle_points",
                move=int(move) if move else None,
            )
        )
    if not 30 <= len(offers) <= 64 or "GiveItem VAR_SPECIAL_x8004, 1, VAR_SPECIAL_RESULT" not in text:
        raise ValueError("HGSS : catalogue du comptoir incomplet")
    return dict(
        tower=dict(
            source=source,
            tables=tables,
            boss=20,
            ordinary_cap=7,
            link_cap=18,
            rule_fr="Tables indexées par nombre de séries terminées (0 = aucune). À partir de la "
            "septième série : 7 Points Combat en ordinaire, 18 en liaison. Koner vaincu : 20. "
            "La table Wi-Fi décrit le service historique ; l’entraînement Wi-Fi ne rapporte rien.",
        ),
        exchange=dict(
            source=script,
            offers=offers,
            rule_fr="Un objet remis par achat, contre le coût indiqué en Points Combat. "
            "Le contrôle de place dans le Sac est conservé séparément de la quantité remise.",
        ),
    )

"""Quantités dépendant du sac et de commandes persistantes HGSS, sans états inconnus."""


def resolve_quantity_rules(offers: list[dict]) -> list[dict]:
    result = []
    for offer in offers:
        values = offer["values"]
        if offer["bank"] == 874 and offer["command"] == "offer_item" and values == ["inconnue", "inconnue"]:
            offer = offer | dict(
                kind="apricorn_return",
                values=[],
                quantity_rule=dict(kind="matching_deposit", minimum=1, maximum=99, output_per_input=1),
                delay=dict(kind="next_day", flag="FLAG_DAILY_KURT_MAKING_BALLS"),
            )
        elif offer["bank"] == 251 and offer["command"] == "GiveOrTakeSeal" and values[1] == "inconnue":
            offer = offer | dict(
                values=values[:1],
                quantity_rule=dict(
                    kind="moomoo_native_seals",
                    initial=3,
                    capacity=99,
                    order=[29, 34, 39],
                    source="files/fielddata/script/scr_seq/scr_seq_0251_R39R0201.s",
                ),
            )
        elif any(value in {"inconnue", "externe"} for value in values):
            raise ValueError(f"HGSS : offre non résolue : {offer['source']} {offer['instruction']} {values}")
        result.append(offer)
    return result


def moomoo_seal_quantities(counts: tuple[int, int, int]) -> tuple[int, int, int]:
    if any(not 0 <= value <= 99 for value in counts):
        raise ValueError("HGSS : quantité de Sceaux hors limites")
    if 99 in counts:
        return 0, 0, 0
    quantities = [3, 3, 3]
    for index, count in enumerate(counts):
        if count <= 96:
            break
        quantities[index] -= count - 96
    # GiveOrTakeSeal refuse un lot dépassant la capacité ; le script ne vérifie pas son retour.
    return tuple(quantity if count + quantity <= 99 else 0 for count, quantity in zip(counts, quantities, strict=True))

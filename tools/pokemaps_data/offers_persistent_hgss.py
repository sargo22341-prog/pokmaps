"""Services persistants HGSS : arbres, Pension, livraisons et cartes à gratter."""

from .pret_models import NpcOffer
from .references_hgss import HgssReferences


def persistent_offers(actor: dict, catalog: dict, refs: HgssReferences) -> list[NpcOffer]:
    service = actor.get("standard_service")
    if service is None or service == "std_mystery_gift_deliveryman":
        return []
    if service in {"std_daycare_man", "std_daycare_lady"}:
        return [NpcOffer("daycare", stories=("Retrait : 100 ₽ × (niveaux gagnés + 1).",))]
    if service == "std_apricorn_tree":
        index = actor["event_fields"]["param0"]
        color = catalog["apricorns"]["trees"][index]["color"].removeprefix("APRICORN_")
        name = f"ITEM_{color}_APRICORN"
        number = next(n for n, key in refs.item_names.items() if key == name)
        return [NpcOffer("fruit_tree", item=refs.item(number), stories=("Un Noigrume par récolte quotidienne.",))]
    if service == "std_moms_gift_deliveryman":
        mother = catalog["services"]["mother"]
        return [
            NpcOffer(
                "gift_item",
                item=refs.item(r["item"]),
                quantity=r["quantity"],
                stories=(*mother["steps_fr"], f"Coût déjà débité de l'épargne : {r['cost']} ₽."),
            )
            for r in mother["normal"] + mother["berries"]
        ]
    if service == "std_scratch_card":
        cards = catalog["services"]["scratch_cards"]
        return [
            NpcOffer(
                "scratch_cards",
                quantity=cards["cards"],
                price=cards["cost"],
                currency="battle_points",
                stories=tuple(cards["steps_fr"]),
            )
        ]
    raise ValueError(f"HGSS : service persistant sans conversion : {service}")

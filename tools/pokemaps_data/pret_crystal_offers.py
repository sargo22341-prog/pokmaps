"""Offres propres à Cristal : œuf de la Pension, tuteur, soldes du toit et récompenses de Buena."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .pret_models import NpcOffer
from .pret_source import annotated_lines, macro_args, parse_int, source_lines

if TYPE_CHECKING:
    from .pret_gen2 import Gen2PretRepo
    from .pret_gen2_scripts import ScriptFile


def odd_eggs(repo: Gen2PretRepo) -> list[NpcOffer]:
    """Les quatorze œufs de la table du moteur, réunis par espèce (normal et chromatique)."""
    species = set(repo.species)
    path = repo.path("data/events/odd_eggs.asm")
    lines = source_lines(path)
    mons = [line.split()[1] for line in lines if line.startswith("db ") and line.split()[1] in species]
    levels = [parse_int(code.split()[1]) for code, comment in annotated_lines(path) if comment == "Level"]
    if len(mons) != 14 or len(set(mons)) != 7 or len(levels) != len(mons):
        raise ValueError("odd_eggs.asm : table des quatorze œufs ou niveaux invalide")
    return list(
        dict.fromkeys(
            NpcOffer("gift_egg", pokemon=mon, quantity=level) for mon, level in zip(mons, levels, strict=True)
        )
    )


def buena_prizes(repo: Gen2PretRepo) -> list[NpcOffer]:
    lines = source_lines(repo.path("data/items/buena_prizes.asm"))
    offers = [
        NpcOffer("point_prize", item=item, price=parse_int(points))
        for item, points in (macro_args(line, "db") for line in lines if line.startswith("db "))
    ]
    if len(offers) != 9 or any(offer.price is None or offer.price <= 0 for offer in offers):
        raise ValueError("buena_prizes.asm : table des récompenses invalide")
    return offers


def rooftop_sales(repo: Gen2PretRepo) -> list[NpcOffer]:
    """Les deux listes de soldes : avant et après la Ligue."""
    lines = source_lines(repo.path("data/items/rooftop_sale.asm"))
    offers = [
        NpcOffer("sale", item=item, price=parse_int(price))
        for item, price in (macro_args(line, "dbw") for line in lines if line.startswith("dbw "))
    ]
    counts = [parse_int(line.split()[1]) for line in lines if line.startswith("db ") and line != "db -1"]
    if (
        len(counts) != 2
        or sum(counts) != len(offers)
        or any(offer.price is None or offer.price <= 0 for offer in offers)
    ):
        raise ValueError("rooftop_sale.asm : listes de soldes invalides")
    return offers


def move_tutor_price(source: ScriptFile) -> int:
    lines = source.reachable_lines("MoveTutorScript", checkver=None)
    prices = {parse_int(line.split()[1]) for line in lines if line.startswith("takecoins ")}
    if len(prices) != 1 or min(prices) <= 0:
        raise ValueError(f"{source.path.name} : prix du tuteur absent ou ambigu")
    return prices.pop()


# Scènes, interfaces et liaisons mobiles : ces commandes ne donnent aucun objet ni Pokémon.
NO_OFFER_SPECIALS = frozenset(
    {
        # Cristal : scènes, menus de combat et services mobiles retirés de la version internationale.
        "StubbedTrainerRankings_Healings",
        "AskMobileOrCable",
        "CableClubCheckWhichChris",
        "CheckMobileAdapterStatusSpecial",
        "CheckMysteryGift",
        "CheckPartyFullAfterContest",
        "ContestReturnMons",
        "BugContestJudging",
        "BeastsCheck",
        "InitRoamMons",
        "GiveDratini",  # Modifie les attaques du Minidraco déjà donné par givepoke.
        "RefreshSprites",
        "LoadMapPalettes",
        "DisplayUnownWords",
        "HoOhChamber",
        "OmanyteChamber",
        "PokeSeer",
        "PokemonCenterPC",
        "BattleTowerAction",  # Récompenses indirectes relues dans npc_offers.csv (script de scène externe).
        "BattleTowerBattle",
        "BattleTowerFade",
        "BattleTowerMobileError",
        "BattleTowerRoomMenu",
        "CheckForBattleTowerRules",
        "Menu_ChallengeExplanationCancel",
        "Mobile_SelectThreeMons",
        "LoadOpponentTrainerAndPokemonWithOTSprite",
        "BuenasPassword",
        "AskRememberPassword",
        "MonCheck",
        "CelebiShrineEvent",  # Scène du sanctuaire ; la rencontre est fournie par PokéAPI.
        "CheckCaughtCelebi",
        "SetDayOfWeek",
        "InitialClearDSTFlag",
        "InitialSetDSTFlag",
        "Reset",
        "SetPlayerPalette",
        "UpdatePlayerSprite",
        "ClearBGPalettes",
        "ToggleDecorationsVisibility",
        "ToggleMaptileDecorations",
        "TrainerHouse",
        "DayCareMon1",
        "DayCareMon2",
        "OverworldTownMap",
        "RandomPhoneMon",
        "SampleKenjiBreakCountdown",
        "Function1011f1",  # Contrôles de liaison mobile et menus du Club Link.
        "Function101220",
        "Function101225",
        "Function101231",
        "Function103780",
        "Function1037c2",
        "Function1037eb",
        "Function10383c",
        "Function10387b",
        "Function1700ba",
    }
)

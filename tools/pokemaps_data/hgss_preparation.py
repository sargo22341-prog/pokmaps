"""Contrat préparatoire HGSS, isolé des jeux générables tant que son lecteur DS n'est pas validé."""

from .games import Game, PretFormat, Region, VersionCover

# Les en-têtes natifs vont de 0 à 539 ; ces identifiants composites restent propres à la branche.
HGSS_JOHTO = Region("JOHTO", "NEW_BARK", 993)
HGSS_KANTO = Region("KANTO", "PALLET", 992)

HEARTGOLD_SOULSILVER = Game(
    "heartgold-soulsilver",
    "pokeheartgold",
    (("heartgold", "HEARTGOLD"), ("soulsilver", "SOULSILVER")),
    "heartgold-soulsilver",
    (VersionCover("heartgold", "ho-oh", 0xC9A227), VersionCover("soulsilver", "lugia", 0x9DA9B5)),
    PretFormat.GEN4,
    (HGSS_JOHTO, HGSS_KANTO),
    national_dex=True,
    remake_generation=2,
)

# Ne pas ajouter ce contrat à ALL_GAMES : Gen4PretRepo refuse HGSS, et les aperçus génériques lisent Sinnoh.
PREPARATORY_GAMES: tuple[Game, ...] = (HEARTGOLD_SOULSILVER,)

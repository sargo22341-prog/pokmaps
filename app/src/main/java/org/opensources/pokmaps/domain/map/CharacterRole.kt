package org.opensources.pokmaps.domain.map

/**
 * Ce qu'est un élément de la carte et ce qu'on peut y faire, pour l'afficher en icônes : dresseur à combattre,
 * personnage, objet ou Pokémon, puis ses fonctions (vendre, donner, échanger, soigner…), dans un ordre fixe.
 */
enum class CharacterRole {
    BATTLE,
    CHARACTER,
    OBJECT,
    POKEMON,
    HEAL,
    SHOP,
    GIFT,
    TRADE,
    PRIZES,
    COINS,
    FOSSIL,
    FRUIT_TREE,
    DAYCARE,
    NAME_RATER,
    MOVE_DELETER,
    MOVE_TUTOR,
    GROOMING,
    CABLE_CLUB;

    companion object {
        /** Rôles d'un objet de la carte d'après sa nature et ses offres (vide pour un objet ramassable). */
        fun of(kind: MapObjectKind, offers: Collection<OfferKind>): List<CharacterRole> {
            val identity = when (kind) {
                MapObjectKind.TRAINER -> BATTLE
                MapObjectKind.NPC -> CHARACTER
                MapObjectKind.NPC_OBJECT -> OBJECT
                MapObjectKind.POKEMON, MapObjectKind.NPC_POKEMON -> POKEMON
                MapObjectKind.ITEM, MapObjectKind.HIDDEN_ITEM -> return emptyList()
                MapObjectKind.VENDING_MACHINE, MapObjectKind.PRIZE_VENDOR, MapObjectKind.HEAL_SPOT -> null
            }
            val functions = offers.map { offer -> roleOf(offer) }.toSet()
            return listOfNotNull(identity) + entries.filter { it in functions }
        }

        private fun roleOf(offer: OfferKind): CharacterRole = when (offer) {
            OfferKind.SALE -> SHOP
            OfferKind.GIFT_ITEM, OfferKind.GIFT_POKEMON, OfferKind.GIFT_EGG -> GIFT
            OfferKind.TRADE, OfferKind.EXCHANGE -> TRADE
            OfferKind.PRIZE_ITEM, OfferKind.PRIZE_POKEMON, OfferKind.POINT_PRIZE -> PRIZES
            OfferKind.COIN_SALE, OfferKind.COIN_GIFT -> COINS
            OfferKind.FOSSIL -> FOSSIL
            OfferKind.FRUIT_TREE -> FRUIT_TREE
            OfferKind.HEAL -> HEAL
            OfferKind.CABLE_CLUB -> CABLE_CLUB
            OfferKind.NAME_RATER -> NAME_RATER
            OfferKind.DAYCARE -> DAYCARE
            OfferKind.MOVE_DELETER -> MOVE_DELETER
            OfferKind.GROOMING -> GROOMING
            OfferKind.MOVE_TUTOR -> MOVE_TUTOR
        }
    }
}

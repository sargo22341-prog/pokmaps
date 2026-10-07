package org.opensources.pokmaps.domain.model

/** Façon d'obtenir un Pokémon, pour les filtres du Pokédex (regroupe les méthodes de rencontre PokéAPI). */
enum class ObtainMethod {
    WALK,
    FISHING,
    SURF,
    GIFT,
    STATIC,
    TRADE,
    EVOLUTION;

    /** Pokémon rencontré à l'état sauvage (herbes, grottes, surf, pêche), qu'on peut capturer sur place. */
    val isWild: Boolean
        get() = when (this) {
            WALK, FISHING, SURF -> true
            GIFT, STATIC, TRADE, EVOLUTION -> false
        }

    companion object {
        /**
         * Méthode de rencontre PokéAPI (encounter_method.identifier). Une méthode inconnue (nouveau jeu) est une
         * erreur : elle doit être classée ici pour que ses Pokémon restent visibles dans les filtres.
         */
        fun fromEncounterMethod(identifier: String): ObtainMethod = when (identifier) {
            "walk" -> WALK
            "old-rod", "good-rod", "super-rod" -> FISHING
            "surf" -> SURF
            "gift", "gift-egg" -> GIFT
            "static", "pokeflute" -> STATIC
            "npc-trade" -> TRADE
            else -> throw IllegalArgumentException("Méthode de rencontre inconnue : $identifier")
        }
    }
}

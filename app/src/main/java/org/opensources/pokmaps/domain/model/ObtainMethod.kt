package org.opensources.pokmaps.domain.model

/** Façon d'obtenir un Pokémon, pour les filtres du Pokédex (regroupe les méthodes de rencontre PokéAPI). */
enum class ObtainMethod {
    WALK,
    FISHING,
    SURF,
    HEADBUTT,
    ROCK_SMASH,
    GIFT,
    STATIC,
    TRADE,
    EVOLUTION;

    /** Pokémon rencontré à l'état sauvage (herbes, grottes, surf, pêche), qu'on peut capturer sur place. */
    val isWild: Boolean
        get() = when (this) {
            WALK, FISHING, SURF, HEADBUTT, ROCK_SMASH -> true
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
            "headbutt", "headbutt-low", "headbutt-normal", "headbutt-high" -> HEADBUTT
            "rock-smash" -> ROCK_SMASH
            "gift", "gift-egg" -> GIFT
            "static", "pokeflute", "squirt-bottle", "roaming-grass" -> STATIC
            "npc-trade" -> TRADE
            else -> throw IllegalArgumentException("Méthode de rencontre inconnue : $identifier")
        }
    }
}

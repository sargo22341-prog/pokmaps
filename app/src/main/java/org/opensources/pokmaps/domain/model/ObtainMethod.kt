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

    companion object {
        /** Méthode de rencontre PokéAPI (encounter_method.identifier), null si inconnue. */
        fun fromEncounterMethod(identifier: String): ObtainMethod? = when (identifier) {
            "walk" -> WALK
            "old-rod", "good-rod", "super-rod" -> FISHING
            "surf" -> SURF
            "gift", "gift-egg" -> GIFT
            "static", "pokeflute" -> STATIC
            "npc-trade" -> TRADE
            else -> null
        }
    }
}

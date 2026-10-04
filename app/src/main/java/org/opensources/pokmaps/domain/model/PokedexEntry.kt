package org.opensources.pokmaps.domain.model

/**
 * Pokémon du Pokédex régional d'un jeu, avec ses types de la génération du jeu
 * et ses façons de l'obtenir dans la version choisie (vide s'il n'y est pas disponible).
 */
data class PokedexEntry(
    val number: Int,
    val pokemonId: Int,
    val name: String,
    val nameEn: String = "",
    val types: List<PokemonType> = emptyList(),
    val obtainMethods: Set<ObtainMethod> = emptySet(),
    /** Capturé dans la version choisie. */
    val caught: Boolean = false,
    val favorite: Boolean = false
) {
    val isAvailable: Boolean get() = obtainMethods.isNotEmpty()
}

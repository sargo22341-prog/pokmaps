package org.opensources.pokmaps.domain.map

/** Le Léviator fixe du Lac Colère est toujours chromatique dans les trois jeux de Johto. */
internal object FixedPokemon {
    fun isShiny(mapIdentifier: String?, pokemonId: Int?): Boolean = mapIdentifier == "lake-of-rage" && pokemonId == 130
}

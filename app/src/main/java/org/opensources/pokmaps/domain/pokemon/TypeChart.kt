package org.opensources.pokmaps.domain.pokemon

import org.opensources.pokmaps.domain.model.PokemonType

/** Faiblesses et résistances d'un Pokémon, d'après la table des types de la génération. */
object TypeChart {
    /**
     * @param factors multiplicateur (en %) de chaque couple (type attaquant, type défenseur)
     * @return les types attaquants dont les dégâts ne sont pas normaux, du plus efficace au moins efficace
     */
    fun defensive(
        attackingTypes: List<PokemonType>,
        defendingTypeIds: List<Int>,
        factors: Map<Pair<Int, Int>, Int>
    ): List<TypeMatchup> = attackingTypes
        .map { attacking ->
            val factor = defendingTypeIds.fold(PERCENT) { total, defending ->
                total * (factors[attacking.id to defending] ?: PERCENT) / PERCENT
            }
            TypeMatchup(attacking, factor)
        }
        .filter { it.factor != PERCENT }
        .sortedWith(compareByDescending<TypeMatchup> { it.factor }.thenBy { it.type.id })

    const val PERCENT = 100
}

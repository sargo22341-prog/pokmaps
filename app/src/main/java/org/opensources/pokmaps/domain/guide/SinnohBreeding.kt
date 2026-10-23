package org.opensources.pokmaps.domain.guide

import org.opensources.pokmaps.domain.pokemon.LearnedMove
import org.opensources.pokmaps.domain.pokemon.PokemonDetails

/** Règles des pensions DS ; aucun tirage de personnalité ou de statistique n’est prédit. */
object SinnohBreeding {
    fun babies(pair: BreedingPair, first: ParentValues, second: ParentValues): List<PokemonDetails> =
        DsBreeding.babies(pair, first, second)

    fun natureParent(pair: BreedingPair, first: ParentValues, second: ParentValues): Int? {
        if (first.foreignLanguage != second.foreignLanguage) return null
        val index = when {
            pair.first.id == BreedingRules.DITTO -> 0
            pair.second.id == BreedingRules.DITTO -> 1
            first.sex == ParentSex.FEMALE -> 0
            second.sex == ParentSex.FEMALE -> 1
            else -> return null
        }
        return index.takeIf { (if (it == 0) first else second).item == BreedingItem.EVERSTONE }
    }

    fun inherited(child: PokemonDetails, donor: List<Int>, other: List<Int>, lightBall: Boolean): List<LearnedMove> =
        DsBreeding.inherited(child, donor, other, lightBall)
}

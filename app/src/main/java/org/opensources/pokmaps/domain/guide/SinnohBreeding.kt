package org.opensources.pokmaps.domain.guide

import org.opensources.pokmaps.domain.pokemon.LearnedMove
import org.opensources.pokmaps.domain.pokemon.PokemonDetails

/** Règles des pensions DS ; aucun tirage de personnalité ou de statistique n’est prédit. */
object SinnohBreeding {
    private val incense = mapOf(
        298 to BreedingItem.SEA_INCENSE, 360 to BreedingItem.LAX_INCENSE,
        406 to BreedingItem.ROSE_INCENSE, 433 to BreedingItem.PURE_INCENSE,
        438 to BreedingItem.ROCK_INCENSE, 439 to BreedingItem.ODD_INCENSE,
        440 to BreedingItem.LUCK_INCENSE, 446 to BreedingItem.FULL_INCENSE,
        458 to BreedingItem.WAVE_INCENSE
    )
    private val adults = mapOf(
        298 to 183, 360 to 202, 406 to 315, 433 to 358, 438 to 185,
        439 to 122, 440 to 113, 446 to 143, 458 to 226
    )

    fun babies(pair: BreedingPair, first: ParentValues, second: ParentValues): List<PokemonDetails> {
        val baby = pair.babies.firstOrNull { it.id in incense } ?: return pair.babies
        val id = if (incense.getValue(baby.id) in setOf(first.item, second.item)) baby.id else adults.getValue(baby.id)
        return pair.babies.filter { it.id == id }
    }

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
        BreedingMoves.inherited(child, donor, other, lightBall, hatchLevel = 1)
}

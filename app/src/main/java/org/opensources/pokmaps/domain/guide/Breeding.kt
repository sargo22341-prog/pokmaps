package org.opensources.pokmaps.domain.guide

import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.PokedexEntry
import org.opensources.pokmaps.domain.pokemon.GenderRatio
import org.opensources.pokmaps.domain.pokemon.LearnedMove
import org.opensources.pokmaps.domain.pokemon.PokemonDetails

enum class ParentSex { MALE, FEMALE, GENDERLESS }
enum class BreedingStatus { NO_EGGS, DIFFERENT_GROUPS, SAME_SEX, RELATED_DVS, POSSIBLE, COMPATIBLE }

data class BreedingCatalog(val game: Game, val pokemon: List<PokedexEntry>)

data class BreedingPair(val first: PokemonDetails, val second: PokemonDetails, val babies: List<PokemonDetails>)

data class ParentValues(
    val sex: ParentSex,
    val defense: Int? = null,
    val special: Int? = null,
    val moves: List<Int> = emptyList()
) {
    init {
        require(defense == null || defense in 0..15)
        require(special == null || special in 0..15)
        require(moves.size <= 4 && moves.distinct().size == moves.size)
    }
}

object BreedingRules {
    fun sexes(pokemon: PokemonDetails): List<ParentSex> = when (val gender = pokemon.traits.gender) {
        GenderRatio.Genderless -> listOf(ParentSex.GENDERLESS)

        is GenderRatio.Gendered -> buildList {
            if (gender.femaleEighths < 8) add(ParentSex.MALE)
            if (gender.femaleEighths > 0) add(ParentSex.FEMALE)
        }
    }

    fun status(pair: BreedingPair, first: ParentValues, second: ParentValues): BreedingStatus {
        require(first.sex in sexes(pair.first) && second.sex in sexes(pair.second))
        val a = pair.first
        val b = pair.second
        if (listOf(a, b).any { it.traits.eggGroups.isEmpty() || "Inconnu" in it.traits.eggGroups }) {
            return BreedingStatus.NO_EGGS
        }
        val ditto = a.id == DITTO || b.id == DITTO
        if (a.id == DITTO && b.id == DITTO) return BreedingStatus.NO_EGGS
        if (!ditto && a.traits.eggGroups.none { it in b.traits.eggGroups }) return BreedingStatus.DIFFERENT_GROUPS
        if (!ditto && (first.sex == second.sex || ParentSex.GENDERLESS in setOf(first.sex, second.sex))) {
            return BreedingStatus.SAME_SEX
        }
        if (first.defense == null || second.defense == null || first.special == null || second.special == null) {
            return BreedingStatus.POSSIBLE
        }
        if (first.defense == second.defense &&
            first.special % 8 == second.special % 8
        ) {
            return BreedingStatus.RELATED_DVS
        }
        return BreedingStatus.COMPATIBLE
    }

    fun donorIsFirst(pair: BreedingPair, first: ParentValues, second: ParentValues): Boolean = when {
        pair.first.id == DITTO -> second.sex == ParentSex.FEMALE
        pair.second.id == DITTO -> first.sex != ParentSex.FEMALE
        else -> first.sex == ParentSex.MALE
    }

    /** Ordre des quatre attaques du parent donneur, puis remplacement de la plus ancienne si nécessaire. */
    fun inherited(child: PokemonDetails, donor: List<Int>, other: List<Int>): List<LearnedMove> {
        require(donor.size <= 4 && other.size <= 4)
        val available = (child.levelUpMoves + child.machineMoves + child.eggMoves).associateBy { it.moveId }
        val egg = child.eggMoves.map { it.moveId }.toSet()
        val machines = child.machineMoves.map { it.moveId }.toSet()
        val levels = child.levelUpMoves.map { it.moveId }.toSet()
        val result = child.levelUpMoves.filter {
            it.level <= 5
        }.map { it.moveId }.distinct().takeLast(4).toMutableList()
        for (move in donor) {
            if (move in result || !(move in egg || move in machines || (move in other && move in levels))) continue
            if (result.size == 4) result.removeAt(0)
            result += move
        }
        return result.map { available.getValue(it) }
    }

    const val DITTO = 132
}

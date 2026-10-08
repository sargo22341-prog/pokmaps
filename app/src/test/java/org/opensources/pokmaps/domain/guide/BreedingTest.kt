package org.opensources.pokmaps.domain.guide

import org.junit.Assert.assertEquals
import org.junit.Test
import org.opensources.pokmaps.domain.model.PokemonType
import org.opensources.pokmaps.domain.pokemon.DamageClass
import org.opensources.pokmaps.domain.pokemon.GenderRatio
import org.opensources.pokmaps.domain.pokemon.LearnedMove

class BreedingTest {
    private val male = ParentValues(ParentSex.MALE, 10, 2)
    private val female = ParentValues(ParentSex.FEMALE, 10, 10)

    @Test
    fun defenseAndSpecialModuloEightPreventBreedingEvenWithDitto() {
        val pair = BreedingPair(breedingPokemon(1), breedingPokemon(2), emptyList())
        assertEquals(BreedingStatus.RELATED_DVS, BreedingRules.status(pair, male, female))
        assertEquals(BreedingStatus.COMPATIBLE, BreedingRules.status(pair, male, female.copy(special = 3)))
        assertEquals(BreedingStatus.POSSIBLE, BreedingRules.status(pair, male.copy(special = null), female))
        assertEquals(BreedingStatus.SAME_SEX, BreedingRules.status(pair, male, female.copy(sex = ParentSex.MALE)))
    }

    @Test
    fun dittoAllowsGenderlessSpeciesButNotBabiesNorAnotherDitto() {
        val ditto = breedingPokemon(132, listOf("Métamorph"), GenderRatio.Genderless)
        val genderless = breedingPokemon(81, listOf("Minéral"), GenderRatio.Genderless)
        val values = ParentValues(ParentSex.GENDERLESS, 1, 1)
        assertEquals(
            BreedingStatus.COMPATIBLE,
            BreedingRules.status(
                BreedingPair(ditto, genderless, emptyList()),
                values,
                values.copy(defense = 2)
            )
        )
        assertEquals(
            BreedingStatus.NO_EGGS,
            BreedingRules.status(BreedingPair(ditto, ditto, emptyList()), values, values)
        )
        assertEquals(
            BreedingStatus.NO_EGGS,
            BreedingRules.status(
                BreedingPair(breedingPokemon(175, listOf("Inconnu")), ditto, emptyList()),
                female,
                values
            )
        )
    }

    @Test
    fun inheritanceUsesBothParentsForLevelMovesAndKeepsTheLastFourInOrder() {
        val child = breedingPokemon(1).copy(
            levelUpMoves = listOf(move(1, 1), move(2, 5), move(3, 8)),
            machineMoves = listOf(move(4)),
            eggMoves = listOf(move(5), move(6))
        )
        val actual = BreedingRules.inherited(child, listOf(3, 4, 5, 6), listOf(3))
        assertEquals(listOf(3, 4, 5, 6), actual.map { it.moveId })
        assertEquals(listOf(1, 2), BreedingRules.inherited(child, listOf(3), emptyList()).map { it.moveId })
    }

    private fun move(id: Int, level: Int = 0) = LearnedMove(
        id,
        "Attaque $id",
        PokemonType(1, "normal", "Normal"),
        DamageClass.PHYSICAL,
        40,
        100,
        35,
        level
    )
}

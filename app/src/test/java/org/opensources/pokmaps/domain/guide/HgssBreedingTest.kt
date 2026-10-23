package org.opensources.pokmaps.domain.guide

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.opensources.pokmaps.domain.model.PokemonType
import org.opensources.pokmaps.domain.pokemon.DamageClass
import org.opensources.pokmaps.domain.pokemon.LearnedMove
import org.opensources.pokmaps.domain.pokemon.MoveNote

class HgssBreedingTest {
    @Test
    fun movePassesKeepLevelOneThenEggMachineSharedAndFinallyVoltTackle() {
        val child = breedingPokemon(172).copy(
            levelUpMoves = listOf(move(1, 1), move(2, 5)),
            machineMoves = listOf(move(3)),
            eggMoves = listOf(move(4), move(344).copy(note = MoveNote.LIGHT_BALL_PARENT))
        )
        assertEquals(listOf(1), HgssBreeding.inherited(child, emptyList(), emptyList(), false).map { it.moveId })
        assertEquals(
            listOf(4, 3, 2, 344),
            HgssBreeding.inherited(child, listOf(2, 3, 4), listOf(2), true).map { it.moveId }
        )
        assertEquals(listOf(1, 2), HgssBreeding.inherited(child, listOf(2), listOf(2), false).map { it.moveId })
    }

    private fun move(id: Int, level: Int = 0) =
        LearnedMove(id, "Move $id", PokemonType(1, "normal", "Normal"), DamageClass.PHYSICAL, 40, 100, 35, level)

    @Test
    fun everstoneWorksForEitherSexAndLanguageAndBothStonesAreAlternatives() {
        val male = ParentValues(ParentSex.MALE, item = BreedingItem.EVERSTONE)
        val female = ParentValues(ParentSex.FEMALE, foreignLanguage = true)
        assertEquals(listOf(0), HgssBreeding.natureParents(male, female))
        assertEquals(listOf(1), HgssBreeding.natureParents(female, male))
        assertEquals(listOf(0, 1), HgssBreeding.natureParents(male, female.copy(item = BreedingItem.EVERSTONE)))
        assertTrue(HgssBreeding.natureParents(female, female).isEmpty())
    }

    @Test
    fun allSixPowerItemsForceTheCorrespondingParentIvAndTwoItemsAreAlternatives() {
        val none = ParentValues(ParentSex.FEMALE)
        assertTrue(HgssBreeding.forcedIvs(none, none).isEmpty())
        HgssBreeding.powerItems.forEach { (item, stat) ->
            val parent = ParentValues(ParentSex.MALE, item = item, ivs = List(6) { it })
            assertEquals(listOf(ForcedBreedingIv(0, stat, stat.ordinal)), HgssBreeding.forcedIvs(parent, none))
            assertEquals(listOf(ForcedBreedingIv(1, stat, stat.ordinal)), HgssBreeding.forcedIvs(none, parent))
            assertEquals(2, HgssBreeding.forcedIvs(parent, parent).size)
            assertEquals(null, HgssBreeding.forcedIvs(parent.copy(ivs = List(6) { null }), none).single().value)
        }
    }

    @Test
    fun allNineIncensesSelectTheBabyAndTheirAbsenceSelectsTheAdult() {
        val families = listOf(
            Triple(298, 183, BreedingItem.SEA_INCENSE), Triple(360, 202, BreedingItem.LAX_INCENSE),
            Triple(406, 315, BreedingItem.ROSE_INCENSE), Triple(433, 358, BreedingItem.PURE_INCENSE),
            Triple(438, 185, BreedingItem.ROCK_INCENSE), Triple(439, 122, BreedingItem.ODD_INCENSE),
            Triple(440, 113, BreedingItem.LUCK_INCENSE), Triple(446, 143, BreedingItem.FULL_INCENSE),
            Triple(458, 226, BreedingItem.WAVE_INCENSE)
        )
        families.forEach { (baby, adult, item) ->
            val pair = BreedingPair(
                breedingPokemon(adult),
                breedingPokemon(132),
                listOf(breedingPokemon(baby), breedingPokemon(adult)),
                4
            )
            val first = ParentValues(ParentSex.FEMALE)
            val second = ParentValues(ParentSex.GENDERLESS)
            assertEquals(listOf(adult), HgssBreeding.babies(pair, first, second).map { it.id })
            assertEquals(listOf(baby), HgssBreeding.babies(pair, first.copy(item = item), second).map { it.id })
            assertEquals(listOf(baby), HgssBreeding.babies(pair, first, second.copy(item = item)).map { it.id })
        }
    }
}

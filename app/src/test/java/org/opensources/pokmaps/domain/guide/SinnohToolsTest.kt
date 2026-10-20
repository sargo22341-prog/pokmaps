package org.opensources.pokmaps.domain.guide

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Test
import org.opensources.pokmaps.domain.model.PokemonType
import org.opensources.pokmaps.domain.pokemon.DamageClass
import org.opensources.pokmaps.domain.pokemon.LearnedMove

class SinnohToolsTest {
    private val female = ParentValues(ParentSex.FEMALE)
    private val male = ParentValues(ParentSex.MALE)

    @Test
    fun nineIncensesChooseTheBabyAndEitherParentCanHoldThem() {
        val families = listOf(
            298 to 183, 360 to 202, 406 to 315, 433 to 358, 438 to 185,
            439 to 122, 440 to 113, 446 to 143, 458 to 226
        )
        val items = listOf(
            BreedingItem.SEA_INCENSE, BreedingItem.LAX_INCENSE, BreedingItem.ROSE_INCENSE,
            BreedingItem.PURE_INCENSE, BreedingItem.ROCK_INCENSE, BreedingItem.ODD_INCENSE,
            BreedingItem.LUCK_INCENSE, BreedingItem.FULL_INCENSE, BreedingItem.WAVE_INCENSE
        )
        families.zip(items).forEach { (family, incense) ->
            val (baby, adult) = family
            val pair = BreedingPair(
                breedingPokemon(adult),
                breedingPokemon(132),
                listOf(breedingPokemon(baby), breedingPokemon(adult)),
                4
            )
            assertEquals(listOf(adult), SinnohBreeding.babies(pair, female, male).map { it.id })
            assertEquals(listOf(baby), SinnohBreeding.babies(pair, female.copy(item = incense), male).map { it.id })
            assertEquals(listOf(baby), SinnohBreeding.babies(pair, female, male.copy(item = incense)).map { it.id })
        }
    }

    @Test
    fun everstoneUsesMotherOrDittoAndDifferentLanguagesPreventItsPromise() {
        val pair = BreedingPair(breedingPokemon(1), breedingPokemon(2), emptyList(), 4)
        val stone = female.copy(item = BreedingItem.EVERSTONE)
        assertEquals(0, SinnohBreeding.natureParent(pair, stone, male))
        assertNull(SinnohBreeding.natureParent(pair, stone.copy(foreignLanguage = true), male))
        assertNull(SinnohBreeding.natureParent(pair, female, male.copy(item = BreedingItem.EVERSTONE)))
        val ditto = pair.copy(second = breedingPokemon(132))
        assertNull(SinnohBreeding.natureParent(ditto, stone, male))
        assertEquals(1, SinnohBreeding.natureParent(ditto, stone, male.copy(item = BreedingItem.EVERSTONE)))
        assertEquals(BreedingStatus.COMPATIBLE, BreedingRules.status(pair, female, male))
    }

    @Test
    fun eggsStartAtLevelOneAndKeepSeparateMovePasses() {
        val child = breedingPokemon(1).copy(
            levelUpMoves = listOf(move(1, 1), move(2, 5), move(3, 8)),
            machineMoves = listOf(move(4)),
            eggMoves = listOf(move(5), move(6))
        )
        assertEquals(listOf(1), SinnohBreeding.inherited(child, emptyList(), emptyList(), false).map { it.moveId })
        assertEquals(
            listOf(5, 6, 4, 3),
            SinnohBreeding.inherited(child, listOf(3, 4, 5, 6), listOf(3), false).map { it.moveId }
        )
    }

    @Test
    fun friendshipDistinguishesEngineItemAndDirectScriptChanges() {
        val rules = FriendshipRules.SINNOH
        assertEquals(80, rules.apply(FriendshipEvent.LEVEL, 70, true, true, true))
        assertEquals(79, rules.apply(FriendshipEvent.VITAMIN, 70, true, true, true))
        assertEquals(76, rules.apply(FriendshipEvent.MASSAGE, 70, true, true, true))
        for (value in listOf(0, 99, 100, 199, 200, 255)) {
            assertEquals(
                (value + 47).coerceAtMost(255),
                rules.apply(FriendshipEvent.SPA_LARGE, value, true, true, true)
            )
        }
        assertEquals(0, rules.apply(FriendshipEvent.REVIVAL_HERB, 5, true, true, true))
        assertFalse(FriendshipEvent.GROOMING in rules.events)
    }

    @Test
    fun roamersKeepVersionSpeciesLevelsAndTwentyNineSeparateRoutes() {
        assertEquals(listOf(481, 488), Roamers.pokemonIds(12))
        assertEquals(Roamers.pokemonIds(12), Roamers.pokemonIds(13))
        assertEquals(listOf(481, 488, 144, 145, 146), Roamers.pokemonIds(14))
        assertEquals(60, Roamers.level(14, 144))
        assertEquals(50, Roamers.level(14, 481))
        assertEquals(29, SinnohRoamerObservations.places.size)
        SinnohRoamerObservations.validate(14, mapOf(144 to "route-204-north"))
    }

    @Test(expected = IllegalArgumentException::class)
    fun diamondCannotObservePlatinumBirds() {
        SinnohRoamerObservations.validate(12, mapOf(144 to "route-201"))
    }

    private fun move(id: Int, level: Int = 0) =
        LearnedMove(id, "Attaque $id", PokemonType(1, "normal", "Normal"), DamageClass.PHYSICAL, 40, 100, 35, level)
}

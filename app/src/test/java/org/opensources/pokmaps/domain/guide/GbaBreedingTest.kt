package org.opensources.pokmaps.domain.guide

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import org.opensources.pokmaps.domain.model.PokemonType
import org.opensources.pokmaps.domain.model.VersionGroup
import org.opensources.pokmaps.domain.pokemon.DamageClass
import org.opensources.pokmaps.domain.pokemon.GenderRatio
import org.opensources.pokmaps.domain.pokemon.LearnedMove
import org.opensources.pokmaps.domain.pokemon.Machine
import org.opensources.pokmaps.domain.pokemon.MoveNote

class GbaBreedingTest {
    private val female = ParentValues(ParentSex.FEMALE, 10, 10)
    private val male = ParentValues(ParentSex.MALE, 10, 2)

    @Test
    fun identicalValuesDoNotPreventGbaBreedingAndIvsHaveTheirOwnRange() {
        val pair = BreedingPair(breedingPokemon(1), breedingPokemon(2), emptyList(), 3)
        assertEquals(BreedingStatus.COMPATIBLE, BreedingRules.status(pair, female, male))
        assertEquals(List(6) { 31 }, female.copy(ivs = List(6) { 31 }).ivs)
    }

    @Test(expected = IllegalArgumentException::class)
    fun ivsAboveThirtyOneAreRejected() {
        female.copy(ivs = listOf(32, null, null, null, null, null))
    }

    @Test
    fun incenseChangesTheBabyAndEitherParentCanHoldIt() {
        val pair = BreedingPair(
            breedingPokemon(183),
            breedingPokemon(132),
            listOf(breedingPokemon(298), breedingPokemon(183)),
            3
        )
        assertEquals(listOf(183), GbaBreeding.babies(pair, female, male).map { it.id })
        assertEquals(
            listOf(298),
            GbaBreeding.babies(pair, female, male.copy(item = BreedingItem.SEA_INCENSE)).map {
                it.id
            }
        )
        val wobbuffet = pair.copy(babies = listOf(breedingPokemon(360), breedingPokemon(202)))
        assertEquals(listOf(202), GbaBreeding.babies(wobbuffet, female, male).map { it.id })
        assertEquals(
            listOf(360),
            GbaBreeding.babies(
                wobbuffet,
                female.copy(item = BreedingItem.LAX_INCENSE),
                male
            ).map { it.id }
        )
    }

    @Test
    fun everstoneIsEmeraldOnlyAndDittoTakesPriorityOverTheFemale() {
        val pair = BreedingPair(breedingPokemon(1), breedingPokemon(2), emptyList(), 3)
        val stone = female.copy(item = BreedingItem.EVERSTONE)
        assertNull(GbaBreeding.natureParent(pair, stone, male, VersionGroup.RUBY_SAPPHIRE))
        assertNull(GbaBreeding.natureParent(pair, stone, male, VersionGroup.FIRERED_LEAFGREEN))
        assertEquals(0, GbaBreeding.natureParent(pair, stone, male, VersionGroup.EMERALD))
        val maleStone = male.copy(item = BreedingItem.EVERSTONE)
        assertNull(GbaBreeding.natureParent(pair, female, maleStone, VersionGroup.EMERALD))
        val ditto = pair.copy(second = breedingPokemon(132, listOf("Métamorph"), GenderRatio.Genderless))
        assertNull(GbaBreeding.natureParent(ditto, stone, ParentValues(ParentSex.GENDERLESS), VersionGroup.EMERALD))
        assertEquals(
            1,
            GbaBreeding.natureParent(
                ditto,
                stone,
                ParentValues(ParentSex.GENDERLESS, item = BreedingItem.EVERSTONE),
                VersionGroup.EMERALD
            )
        )
    }

    @Test
    fun gbaUsesSeparateEggMachineAndSharedLevelPassesThenAddsVoltTackle() {
        val child = breedingPokemon(172).copy(
            levelUpMoves = listOf(move(1, 1), move(2, 5), move(3, 8)),
            machineMoves = listOf(move(4).copy(machine = Machine("tm01", "CT01"))),
            eggMoves = listOf(move(5), move(6), move(344).copy(note = MoveNote.LIGHT_BALL_PARENT))
        )
        assertEquals(
            listOf(5, 6, 4, 3),
            GbaBreeding.inherited(child, listOf(3, 4, 5, 6), listOf(3), false).map { it.moveId }
        )
        assertEquals(
            listOf(6, 4, 3, 344),
            GbaBreeding.inherited(child, listOf(3, 4, 5, 6), listOf(3), true).map { it.moveId }
        )
        assertEquals(listOf(1, 2), GbaBreeding.inherited(child, listOf(344), emptyList(), false).map { it.moveId })
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

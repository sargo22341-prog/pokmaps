package org.opensources.pokmaps.domain.map

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class TeamSelectionTest {
    private fun team(variant: TeamVariant?, pokemonId: Int, rematch: Int? = null) =
        TrainerTeam(variant, listOf(TrainerPokemon(pokemonId, "n$pokemonId", 5, emptyList())), rematch)

    private fun starter(id: Int) = TeamVariant(TeamVariantKind.PLAYER_STARTER, id, "s$id")

    private fun evolution(id: Int) = TeamVariant(TeamVariantKind.RIVAL_EVOLUTION, id, "e$id")

    private val rival = listOf(team(starter(4), 7), team(starter(7), 1), team(starter(1), 4))

    @Test
    fun aTrainerWithOneTeamHasNothingToChoose() {
        val teams = listOf(team(null, 19), team(null, 20, rematch = 1))
        val selection = TeamSelection.of(teams, RivalChoice(starterId = 4))
        assertEquals(teams, selection.shown)
        assertTrue(selection.variants.isEmpty())
        assertNull(selection.kind)
    }

    @Test
    fun startersAreOfferedInPokedexOrderAndTheFirstIsShownUntilChosen() {
        val selection = TeamSelection.of(rival, RivalChoice())
        assertEquals(listOf(1, 4, 7), selection.variants.map { it.pokemonId })
        assertEquals(starter(1), selection.selected)
        assertEquals(listOf(4), selection.shown.flatMap { team -> team.members.map { it.pokemonId } })
    }

    @Test
    fun theChosenStarterGivesTheRivalItsCounter() {
        val selection = TeamSelection.of(rival, RivalChoice(starterId = 4))
        assertEquals(TeamVariantKind.PLAYER_STARTER, selection.kind)
        assertEquals(listOf(7), selection.shown.flatMap { team -> team.members.map { it.pokemonId } })
    }

    @Test
    fun aStarterFromAnotherGameFallsBackToTheFirstTeam() {
        assertEquals(starter(1), TeamSelection.of(rival, RivalChoice(starterId = 152)).selected)
    }

    @Test
    fun yellowEeveeFollowsTheFirstTwoBattles() {
        assertEquals(JOLTEON, RivalChoice(wonLabBattle = true, wonRoute22Battle = true).rivalEvolutionId)
        assertEquals(FLAREON, RivalChoice(wonLabBattle = true, wonRoute22Battle = false).rivalEvolutionId)
        assertEquals(VAPOREON, RivalChoice(wonLabBattle = false, wonRoute22Battle = true).rivalEvolutionId)
        assertEquals(VAPOREON, RivalChoice(wonLabBattle = false, wonRoute22Battle = false).rivalEvolutionId)
    }

    @Test
    fun yellowRivalTeamFollowsTheBattles() {
        val teams = listOf(team(evolution(JOLTEON), 1), team(evolution(FLAREON), 2), team(evolution(VAPOREON), 3))
        val selection = TeamSelection.of(teams, RivalChoice(wonLabBattle = true, wonRoute22Battle = false))
        assertEquals(evolution(FLAREON), selection.selected)
        assertEquals(listOf(teams[1]), selection.shown)
    }

    @Test(expected = IllegalArgumentException::class)
    fun mixedVariantKindsAreRejected() {
        TeamSelection.of(listOf(team(starter(1), 4), team(evolution(JOLTEON), 1)), RivalChoice())
    }

    @Test
    fun noTeamMeansItIsUnknown() {
        assertTrue(TeamSelection.of(emptyList(), RivalChoice()).unknown)
    }

    @Test
    fun yellowOnlyOffersEvolutionChoicesForTheSecondRoute22Battle() {
        val fixed = team(null, 133)
        val variants = listOf(JOLTEON, FLAREON, VAPOREON).map { team(evolution(it), it, rematch = 1) }
        val selection = TeamSelection.of(listOf(fixed) + variants, RivalChoice())
        val first = selection.forBattle(null)
        assertEquals(listOf(fixed), first.shown)
        assertTrue(first.variants.isEmpty())
        assertNull(first.selected)
        val second = selection.forBattle(1)
        assertEquals(selection.variants, second.variants)
        assertEquals(evolution(JOLTEON), second.selected)
        assertEquals(listOf(JOLTEON), second.shown.flatMap { it.members }.map { it.pokemonId })
    }

    private companion object {
        const val VAPOREON = 134
        const val JOLTEON = 135
        const val FLAREON = 136
    }
}

package org.opensources.pokmaps.ui.guide

import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.domain.guide.BreedingCatalog
import org.opensources.pokmaps.domain.guide.BreedingPair
import org.opensources.pokmaps.domain.guide.ParentSex
import org.opensources.pokmaps.domain.guide.ParentValues
import org.opensources.pokmaps.domain.guide.breedingPokemon
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.PokedexEntry
import org.opensources.pokmaps.domain.pokemon.GenderRatio
import org.opensources.pokmaps.domain.usecase.BreedingTools
import org.opensources.pokmaps.ui.MainDispatcherRule

class BreedingViewModelTest {
    @get:Rule val mainDispatcher = MainDispatcherRule()

    @Test
    fun emptyFirstGenerationCatalogIsNotAnError() = runTest {
        val tools = MemoryBreeding()
        tools.catalog.value = BreedingCatalog(FakeGameDao.RED, emptyList())
        val model = BreedingViewModel(tools)
        assertFalse(model.state.value.loading)
        assertFalse(model.state.value.failed)
        assertEquals(null, model.state.value.pair)
        assertEquals(0, tools.pairCalls)
    }

    @Test
    fun failureIsVisibleAndRetryLoadsParents() = runTest {
        val tools = MemoryBreeding()
        tools.failing = true
        val model = BreedingViewModel(tools)
        assertTrue(model.state.value.failed)
        tools.failing = false
        model.onAction(BreedingAction.Retry)
        assertFalse(model.state.value.failed)
        assertFalse(model.state.value.loading)
        assertTrue(model.state.value.possible)
    }

    @Test
    fun parentSearchAcceptsAccentsAndNumbersAndLeavesThePairUntouched() = runTest {
        val tools = MemoryBreeding()
        val model = BreedingViewModel(tools)
        model.onAction(BreedingAction.Search("metamorph"))
        assertEquals(listOf(132), model.state.value.choices.map { it.pokemonId })
        model.onAction(BreedingAction.Search("#002"))
        assertEquals(listOf(2), model.state.value.choices.map { it.pokemonId })
        model.onAction(BreedingAction.Search("introuvable"))
        assertTrue(model.state.value.choices.isEmpty())
        model.onAction(BreedingAction.Search(""))
        assertEquals(3, model.state.value.choices.size)
        assertEquals(1, tools.pairCalls)
    }

    @Test
    fun changingSpeciesClearsOnlyItsDvsAndPreservesTheOtherParent() = runTest {
        val model = BreedingViewModel(MemoryBreeding())
        model.onAction(BreedingAction.Values(true, ParentValues(ParentSex.FEMALE, 1, 2)))
        model.onAction(BreedingAction.Values(false, ParentValues(ParentSex.GENDERLESS, 3, 4)))
        model.onAction(BreedingAction.Species(true, 2))
        assertEquals(null, model.state.value.first.defense)
        assertEquals(3, model.state.value.second.defense)
        assertEquals(4, model.state.value.second.special)
    }
}

private class MemoryBreeding : BreedingTools {
    val catalog = MutableStateFlow(
        BreedingCatalog(
            FakeGameDao.GOLD,
            listOf(
                PokedexEntry(1, 1, "Bulbizarre"),
                PokedexEntry(2, 2, "Herbizarre"),
                PokedexEntry(132, 132, "Métamorph")
            )
        )
    )
    var failing = false
    var pairCalls = 0
    override fun observe(): Flow<BreedingCatalog> = if (failing) flow { error("Base illisible") } else catalog
    override suspend fun pair(game: Game, firstId: Int, secondId: Int, firstSex: ParentSex): BreedingPair {
        pairCalls += 1
        return BreedingPair(
            breedingPokemon(firstId),
            breedingPokemon(
                secondId,
                listOf("Métamorph"),
                GenderRatio.Genderless
            ),
            listOf(breedingPokemon(1))
        )
    }
}

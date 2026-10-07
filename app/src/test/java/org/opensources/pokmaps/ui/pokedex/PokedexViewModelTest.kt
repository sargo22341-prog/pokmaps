package org.opensources.pokmaps.ui.pokedex

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.data.db.FakePokedexDao
import org.opensources.pokmaps.data.db.FakePokedexDao.Companion.POISON
import org.opensources.pokmaps.data.db.PokedexDao
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.repository.PokedexRepository
import org.opensources.pokmaps.data.settings.CollectionSettings
import org.opensources.pokmaps.data.settings.FakeDataStore
import org.opensources.pokmaps.data.settings.GameSettings
import org.opensources.pokmaps.domain.model.ObtainMethod
import org.opensources.pokmaps.domain.pokedex.CaughtFilter
import org.opensources.pokmaps.domain.usecase.ObserveCollectionUseCase
import org.opensources.pokmaps.domain.usecase.ObservePokedexUseCase
import org.opensources.pokmaps.domain.usecase.UpdateCollectionUseCase
import org.opensources.pokmaps.ui.MainDispatcherRule

@OptIn(ExperimentalCoroutinesApi::class)
class PokedexViewModelTest {
    private val red = FakeGameDao.RED
    private val blue = FakeGameDao.BLUE

    @get:Rule
    val mainDispatcher = MainDispatcherRule()

    private val dataStore = FakeDataStore()
    private val settings = GameSettings(dataStore)
    private val viewModel by lazy { pokedexViewModel(FakePokedexDao()) }

    private fun pokedexViewModel(dao: PokedexDao): PokedexViewModel {
        val collection = CollectionSettings(dataStore)
        val games = GameRepository(FakeGameDao(), settings)
        return PokedexViewModel(
            ObservePokedexUseCase(games, PokedexRepository(dao)),
            ObserveCollectionUseCase(games, collection),
            UpdateCollectionUseCase(games, collection)
        )
    }

    private fun ids() = viewModel.state.value.entries.map { it.pokemonId }

    @Test
    fun loadsThePokedexOfTheSelectedGame() = runTest {
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        val state = viewModel.state.value
        assertFalse(state.loading)
        assertEquals(red, state.game)
        assertEquals(listOf(23, 24, 27, 133, 134), ids())
        assertEquals(5, state.total)
        assertEquals(listOf("Normal", "Poison", "Sol", "Eau"), state.types.map { it.name })
        assertEquals(setOf(ObtainMethod.WALK), state.entries.first().obtainMethods)
    }

    @Test
    fun searchIgnoresAccents() = runTest {
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        viewModel.onAction(PokedexAction.Search("evoli"))
        assertEquals(listOf(133), ids())
        viewModel.onAction(PokedexAction.Search("134"))
        assertEquals(listOf(134), ids())
    }

    @Test
    fun availabilityDependsOnTheVersion() = runTest {
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        viewModel.onAction(PokedexAction.ToggleAvailableOnly)
        // Abo et Arbok en Rouge, Sabelette en Bleu ; Aquali évolue d'Évoli (don).
        assertEquals(listOf(23, 24, 133, 134), ids())
        settings.selectVersion(blue.versionId)
        assertEquals(blue, viewModel.state.value.game)
        assertEquals(listOf(27, 133, 134), ids())
    }

    @Test
    fun filtersByTypeAndMethodThenResets() = runTest {
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        viewModel.onAction(PokedexAction.Search("a"))
        viewModel.onAction(PokedexAction.FilterType(POISON))
        assertEquals(listOf(23, 24), ids())
        viewModel.onAction(PokedexAction.FilterType(null))
        viewModel.onAction(PokedexAction.FilterMethod(ObtainMethod.EVOLUTION))
        assertEquals(listOf(24, 134), ids())
        viewModel.onAction(PokedexAction.ResetFilters)
        assertNull(viewModel.state.value.filter.method)
        assertEquals("a", viewModel.state.value.filter.query)
    }

    @Test
    fun startsLoading() {
        val state = pokedexViewModel(FakePokedexDao()).state.value
        assertTrue(state.loading)
        assertFalse(state.failed)
    }

    @Test
    fun aFilterWithoutMatchIsEmptyNotAnError() = runTest {
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        viewModel.onAction(PokedexAction.Search("mewtwo"))
        val state = viewModel.state.value
        assertTrue(state.entries.isEmpty())
        assertFalse(state.failed)
        assertEquals(5, state.total)
    }

    @Test
    fun anUnreadableDatabaseIsAnError() = runTest {
        val failing = pokedexViewModel(FakePokedexDao(failing = true))
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { failing.state.collect {} }
        val state = failing.state.value
        assertTrue(state.failed)
        assertFalse(state.loading)
        assertTrue(state.entries.isEmpty())
    }

    @Test
    fun caughtPokemonAreTrackedPerVersionAndFavoritesAcrossGames() = runTest {
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        val abo = viewModel.state.value.entries.first { it.pokemonId == 23 }
        viewModel.onAction(PokedexAction.ToggleCaught(abo))
        viewModel.onAction(PokedexAction.ToggleFavorite(abo))
        assertEquals(1, viewModel.state.value.caughtCount)
        viewModel.onAction(PokedexAction.FilterCaught(CaughtFilter.CAUGHT))
        assertEquals(listOf(23), ids())
        viewModel.onAction(PokedexAction.FilterCaught(CaughtFilter.MISSING))
        assertEquals(listOf(24, 27, 133, 134), ids())
        viewModel.onAction(PokedexAction.FilterCaught(CaughtFilter.ALL))
        viewModel.onAction(PokedexAction.ToggleFavoritesOnly)
        assertEquals(listOf(23), ids())
        // Bleu : rien de capturé dans cette version, mais les favoris sont communs à tous les jeux.
        settings.selectVersion(blue.versionId)
        assertEquals(0, viewModel.state.value.caughtCount)
        assertEquals(listOf(23), ids())
        assertFalse(viewModel.state.value.entries.single().caught)
        assertTrue(viewModel.state.value.entries.single().favorite)
    }
}

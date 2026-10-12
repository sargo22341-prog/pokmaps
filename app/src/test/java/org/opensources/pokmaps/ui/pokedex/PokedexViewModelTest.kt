package org.opensources.pokmaps.ui.pokedex

import java.io.IOException
import kotlinx.coroutines.CancellationException
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
import org.opensources.pokmaps.data.db.PokedexCatalogRow
import org.opensources.pokmaps.data.db.PokedexDao
import org.opensources.pokmaps.data.db.PokedexRow
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

    private fun pokedexViewModel(dao: PokedexDao, availableGames: FakeGameDao = FakeGameDao()): PokedexViewModel {
        val collection = CollectionSettings(dataStore)
        val games = GameRepository(availableGames, settings)
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

    @Test
    fun switchesDexWithoutLosingFiltersOrCollectionAndResetsWhenChangingGame() = runTest {
        val games = FakeGameDao(listOf(FakeGameDao.EMERALD, FakeGameDao.FIRERED, red))
        val model = pokedexViewModel(FakePokedexDao(national = true), games)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { model.state.collect {} }
        assertEquals(4, model.state.value.selectedPokedexId)
        assertEquals(listOf(252), model.state.value.entries.map { it.pokemonId })
        model.onAction(PokedexAction.Search("a"))
        model.onAction(PokedexAction.ToggleCaught(model.state.value.entries.single()))
        model.onAction(PokedexAction.SelectPokedex(1))
        assertEquals(1, model.state.value.selectedPokedexId)
        assertEquals("a", model.state.value.filter.query)
        assertEquals(listOf(23, 24, 27, 134), model.state.value.entries.map { it.pokemonId })
        model.onAction(PokedexAction.SelectPokedex(999))
        assertEquals(1, model.state.value.selectedPokedexId)
        model.onAction(PokedexAction.SelectPokedex(4))
        assertTrue(model.state.value.entries.single().caught)
        model.onAction(PokedexAction.SelectPokedex(1))
        settings.selectVersion(FakeGameDao.FIRERED.versionId)
        assertEquals(2, model.state.value.selectedPokedexId)
        settings.selectVersion(red.versionId)
        assertEquals(2, model.state.value.selectedPokedexId)
    }

    @Test
    fun missingDexIsAnErrorAndEmptyDexRemainsValid() = runTest {
        val missing = object : PokedexDao by FakePokedexDao() {
            override suspend fun catalogs(versionGroupId: Int) = emptyList<PokedexCatalogRow>()
        }
        val model = pokedexViewModel(missing)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { model.state.collect {} }
        assertTrue(model.state.value.failed)
        val empty = object : PokedexDao by FakePokedexDao() {
            override suspend fun pokedex(versionGroupId: Int, pokedexId: Int) = emptyList<PokedexRow>()
        }
        val emptyModel = pokedexViewModel(empty)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { emptyModel.state.collect {} }
        assertFalse(emptyModel.state.value.failed)
        assertEquals(0, emptyModel.state.value.total)
    }

    @Test
    fun failedCollectionWritesKeepPreviousValuesAndCanBeRetried() = runTest {
        val model = viewModel
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { model.state.collect {} }
        dataStore.writeError = IOException("Écriture impossible")
        model.onAction(PokedexAction.ToggleCaught(model.state.value.entries.first()))
        assertTrue(model.state.value.writeFailed)
        assertFalse(model.state.value.entries.first().caught)
        assertFalse(model.state.value.failed)
        dataStore.writeError = null
        model.onAction(PokedexAction.ToggleCaught(model.state.value.entries.first()))
        assertTrue(model.state.value.entries.first().caught)
        assertFalse(model.state.value.writeFailed)
        dataStore.writeError = IOException("Écriture impossible")
        model.onAction(PokedexAction.ToggleFavorite(model.state.value.entries.first()))
        assertTrue(model.state.value.writeFailed)
        assertFalse(model.state.value.entries.first().favorite)
        assertTrue(model.state.value.entries.first().caught)
        dataStore.writeError = null
        model.onAction(PokedexAction.ToggleFavorite(model.state.value.entries.first()))
        assertTrue(model.state.value.entries.first().favorite)
        assertFalse(model.state.value.writeFailed)
    }

    @Test
    fun cancelledCollectionWriteDoesNotBecomeAnError() = runTest {
        val model = viewModel
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { model.state.collect {} }
        dataStore.writeError = CancellationException("Annulation")
        model.onAction(PokedexAction.ToggleCaught(model.state.value.entries.first()))
        model.onAction(PokedexAction.ToggleFavorite(model.state.value.entries.first()))
        assertFalse(model.state.value.writeFailed)
        assertFalse(model.state.value.entries.first().caught)
        assertFalse(model.state.value.entries.first().favorite)
    }
}

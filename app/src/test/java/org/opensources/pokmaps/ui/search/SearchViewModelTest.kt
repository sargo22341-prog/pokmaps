package org.opensources.pokmaps.ui.search

import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.data.db.FakeMapDao
import org.opensources.pokmaps.data.db.FakePokedexDao
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.repository.MapRepository
import org.opensources.pokmaps.data.repository.PokedexRepository
import org.opensources.pokmaps.data.settings.FakeDataStore
import org.opensources.pokmaps.data.settings.GameSettings
import org.opensources.pokmaps.domain.usecase.ObserveSearchIndexUseCase
import org.opensources.pokmaps.ui.MainDispatcherRule

@OptIn(ExperimentalCoroutinesApi::class)
class SearchViewModelTest {
    @get:Rule
    val mainDispatcher = MainDispatcherRule()

    private fun viewModel(
        failing: Boolean = false,
        composite: Boolean = false,
        computation: CoroutineDispatcher = Dispatchers.Unconfined
    ): SearchViewModel {
        val games = GameRepository(FakeGameDao(), GameSettings(FakeDataStore()))
        return SearchViewModel(
            ObserveSearchIndexUseCase(
                games,
                PokedexRepository(FakePokedexDao()),
                MapRepository(FakeMapDao(failing, includeCompositeInterior = composite), Dispatchers.Unconfined)
            ),
            computation
        )
    }

    @Test
    fun startsLoading() {
        assertTrue(viewModel().state.value.loading)
    }

    @Test
    fun theIndexIsBuiltAndFilteredOnTheComputationDispatcher() = runTest {
        val computation = StandardTestDispatcher(testScheduler)
        val viewModel = viewModel(computation = computation)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        viewModel.onAction(SearchAction.Query("evoli"))
        // Rien n'est calculé sur le fil de l'appelant : l'état attend le répartiteur de calcul.
        assertTrue(viewModel.state.value.loading)

        testScheduler.advanceUntilIdle()

        assertFalse(viewModel.state.value.loading)
        assertEquals(listOf(133), viewModel.state.value.pokemon.map { it.pokemonId })
    }

    @Test
    fun theTypedTextReachesTheStateBeforeTheResults() = runTest {
        val computation = StandardTestDispatcher(testScheduler)
        val viewModel = viewModel(computation = computation)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        testScheduler.advanceUntilIdle()
        viewModel.onAction(SearchAction.Query("e"))
        viewModel.onAction(SearchAction.Query("ev"))
        // Le champ relit aussitôt sa valeur : un retard replaçait le curseur avant les lettres déjà tapées.
        assertEquals("ev", viewModel.state.value.query)

        testScheduler.advanceUntilIdle()

        assertEquals("ev", viewModel.state.value.query)
        assertTrue(133 in viewModel.state.value.pokemon.map { it.pokemonId })
    }

    @Test
    fun aRoomOnAComposedFloorIsAnInteriorSearchResult() = runTest {
        val viewModel = viewModel(composite = true)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        viewModel.onAction(SearchAction.Query("jadielle"))
        val places = viewModel.state.value.places
        assertTrue(places.single { it.identifier == "viridian-city" }.outdoor)
        assertFalse(places.single { it.identifier == "viridian-mart" }.outdoor)
    }

    @Test
    fun aBlankQueryShowsNoResult() = runTest {
        val viewModel = viewModel()
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        val state = viewModel.state.value
        assertFalse(state.loading)
        assertEquals(FakeGameDao.RED, state.game)
        assertTrue(state.isEmpty)
    }

    @Test
    fun findsPokemonPlacesItemsAndCharactersIgnoringAccents() = runTest {
        val viewModel = viewModel()
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        viewModel.onAction(SearchAction.Query("evoli"))
        assertEquals(listOf(133), viewModel.state.value.pokemon.map { it.pokemonId })
        viewModel.onAction(SearchAction.Query("jadielle"))
        assertEquals(listOf("viridian-city", "viridian-mart"), viewModel.state.value.places.map { it.identifier })
        viewModel.onAction(SearchAction.Query("potion"))
        val state = viewModel.state.value
        assertEquals(listOf("potion"), state.items.map { it.identifier })
        // Le vendeur est trouvé par ce qu'il vend.
        assertEquals(listOf(FakeMapDao.CLERK), state.characters.map { it.obj.id })
    }

    @Test
    fun aQueryWithoutMatchIsEmptyNotAnError() = runTest {
        val viewModel = viewModel()
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        viewModel.onAction(SearchAction.Query("zzz"))
        assertTrue(viewModel.state.value.isEmpty)
        assertFalse(viewModel.state.value.failed)
    }

    @Test
    fun anUnreadableDatabaseIsAnError() = runTest {
        val viewModel = viewModel(failing = true)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        assertTrue(viewModel.state.value.failed)
        assertFalse(viewModel.state.value.loading)
    }
}

package org.opensources.pokmaps.ui.pokemon

import androidx.lifecycle.SavedStateHandle
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
import org.opensources.pokmaps.data.db.FakePokemonDao
import org.opensources.pokmaps.data.db.FakePokemonDao.Companion.PIKACHU
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.repository.PokedexRepository
import org.opensources.pokmaps.data.repository.PokemonRepository
import org.opensources.pokmaps.data.settings.CollectionSettings
import org.opensources.pokmaps.data.settings.FakeDataStore
import org.opensources.pokmaps.data.settings.GameSettings
import org.opensources.pokmaps.domain.pokemon.Ball
import org.opensources.pokmaps.domain.pokemon.CatchStatus
import org.opensources.pokmaps.domain.usecase.MapRequest
import org.opensources.pokmaps.domain.usecase.MapRequests
import org.opensources.pokmaps.domain.usecase.ObserveCollectionUseCase
import org.opensources.pokmaps.domain.usecase.ObservePokemonUseCase
import org.opensources.pokmaps.domain.usecase.UpdateCollectionUseCase
import org.opensources.pokmaps.ui.MainDispatcherRule

@OptIn(ExperimentalCoroutinesApi::class)
class PokemonViewModelTest {
    @get:Rule
    val mainDispatcher = MainDispatcherRule()

    private val requests = MapRequests()

    private fun viewModel(pokemonId: Int, failing: Boolean = false): PokemonViewModel {
        val dataStore = FakeDataStore()
        val games = GameRepository(FakeGameDao(), GameSettings(dataStore))
        val collection = CollectionSettings(dataStore)
        val repository = PokemonRepository(FakePokemonDao(failing), PokedexRepository(FakePokedexDao()))
        return PokemonViewModel(
            SavedStateHandle(mapOf(PokemonViewModel.POKEMON_ID to pokemonId)),
            ObservePokemonUseCase(games, repository),
            ObserveCollectionUseCase(games, collection),
            UpdateCollectionUseCase(collection),
            requests
        )
    }

    @Test
    fun startsLoading() {
        assertEquals(PokemonUiState(), viewModel(PIKACHU).state.value)
    }

    @Test
    fun detailsCollectionAndMapRequest() = runTest {
        val viewModel = viewModel(PIKACHU)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        assertEquals("Pikachu", viewModel.state.value.details?.name)
        viewModel.onAction(PokemonAction.ToggleCaught)
        viewModel.onAction(PokemonAction.ToggleFavorite)
        assertTrue(viewModel.state.value.caught)
        assertTrue(viewModel.state.value.favorite)
        viewModel.onAction(PokemonAction.ShowOnMap)
        assertEquals(MapRequest.HighlightPokemon(PIKACHU, "Pikachu"), requests.pending.value)
    }

    @Test
    fun catchCalculatorFollowsTheInputs() = runTest {
        val viewModel = viewModel(PIKACHU)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        viewModel.onAction(PokemonAction.SetCatchLevel(500))
        viewModel.onAction(PokemonAction.SetCatchHp(HpChoice.ONE))
        viewModel.onAction(PokemonAction.SetCatchStatus(CatchStatus.SLEEP_OR_FREEZE))
        val catch = checkNotNull(viewModel.state.value.catch)
        assertEquals(PokemonViewModel.MAX_LEVEL, catch.level)
        assertEquals(1.0, catch.probabilities.toMap().getValue(Ball.MASTER), 0.0)
    }

    @Test
    fun anUnknownPokemonIsNotFoundNotAnError() = runTest {
        val viewModel = viewModel(pokemonId = 999)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        val state = viewModel.state.value
        assertNull(state.details)
        assertNull(state.catch)
        assertFalse(state.loading)
        assertFalse(state.failed)
    }

    @Test
    fun anUnreadableDatabaseIsAnError() = runTest {
        val viewModel = viewModel(PIKACHU, failing = true)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        assertTrue(viewModel.state.value.failed)
        assertNull(viewModel.state.value.details)
    }
}

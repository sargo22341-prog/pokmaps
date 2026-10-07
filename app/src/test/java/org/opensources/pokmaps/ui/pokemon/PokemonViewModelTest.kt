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
import org.opensources.pokmaps.domain.pokedex.CaptureScope
import org.opensources.pokmaps.domain.pokemon.Ball
import org.opensources.pokmaps.domain.pokemon.CatchStatus
import org.opensources.pokmaps.domain.pokemon.GenderRatio
import org.opensources.pokmaps.domain.pokemon.GenerationFeature
import org.opensources.pokmaps.domain.pokemon.HeldItem
import org.opensources.pokmaps.domain.pokemon.Machine
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
    private val dataStore = FakeDataStore()
    private val games = GameRepository(
        FakeGameDao(listOf(FakeGameDao.RED, FakeGameDao.BLUE, FakeGameDao.GOLD)),
        GameSettings(dataStore)
    )
    private val collection = CollectionSettings(dataStore)

    private fun viewModel(pokemonId: Int, failing: Boolean = false): PokemonViewModel {
        val repository = PokemonRepository(FakePokemonDao(failing), PokedexRepository(FakePokedexDao()))
        return PokemonViewModel(
            SavedStateHandle(mapOf(PokemonViewModel.POKEMON_ID to pokemonId)),
            ObservePokemonUseCase(games, repository),
            ObserveCollectionUseCase(games, collection),
            UpdateCollectionUseCase(games, collection),
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
    fun movesLinkToTheirSheetOrToTheirMachine() = runTest {
        val viewModel = viewModel(PIKACHU)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        val details = checkNotNull(viewModel.state.value.details)
        assertEquals(listOf(FakePokemonDao.THUNDER_SHOCK), details.levelUpMoves.map { it.moveId })
        assertNull(details.levelUpMoves.single().machine)
        assertEquals(Machine("tm24", "CT24"), details.machineMoves.single().machine)
    }

    @Test
    fun shinyTogglesTheSpritesOnlyInAGameWithShinies() = runTest {
        val viewModel = viewModel(PIKACHU)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        // Rouge n'a pas de chromatiques : la demande est ignorée.
        viewModel.onAction(PokemonAction.ToggleShiny)
        assertFalse(viewModel.state.value.shiny)

        games.select(FakeGameDao.GOLD)
        assertFalse(viewModel.state.value.shiny)
        viewModel.onAction(PokemonAction.ToggleShiny)
        assertTrue(viewModel.state.value.shiny)
        // Revenir à Rouge rend les couleurs normales ; Or retrouve le choix.
        games.select(FakeGameDao.RED)
        assertFalse(viewModel.state.value.shiny)
        games.select(FakeGameDao.GOLD)
        assertTrue(viewModel.state.value.shiny)
        viewModel.onAction(PokemonAction.ToggleShiny)
        assertFalse(viewModel.state.value.shiny)
    }

    @Test
    fun laterGenerationDataFollowsTheChosenGame() = runTest {
        val viewModel = viewModel(PIKACHU)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        val red = viewModel.state.value
        // 1re génération : ni chromatiques, ni objets tenus, ni talents dans le jeu.
        assertNull(red.shinyOdds)
        assertFalse(red.has(GenerationFeature.HELD_ITEMS))
        assertFalse(red.has(GenerationFeature.ABILITIES))
        assertEquals(emptyList<HeldItem>(), red.details?.traits?.heldItems)
        assertEquals(GenderRatio.Gendered(4), red.details?.traits?.gender)

        // Les objets tenus sont ceux de la version choisie.
        games.select(FakeGameDao.BLUE)
        val blue = viewModel.state.value.details?.traits
        assertEquals(listOf(HeldItem("light-ball", "Ballon Lumière", true, 5)), blue?.heldItems)
        assertEquals(listOf("Terrestre", "Féerique"), blue?.eggGroups)

        // 2e génération : chromatiques et objets tenus apparaissent, pas encore les talents.
        games.select(FakeGameDao.GOLD)
        val gold = viewModel.state.value
        assertEquals(8192, gold.shinyOdds)
        assertTrue(gold.has(GenerationFeature.HELD_ITEMS))
        assertFalse(gold.has(GenerationFeature.ABILITIES))
    }

    @Test
    fun caughtFollowsTheCaptureScope() = runTest {
        val viewModel = viewModel(PIKACHU)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        viewModel.onAction(PokemonAction.ToggleCaught)
        assertTrue(viewModel.state.value.caught)

        // Capturé dans Rouge seulement : pas dans Bleu tant que la portée est le jeu…
        games.select(FakeGameDao.BLUE)
        assertFalse(viewModel.state.value.caught)
        // … mais dans Bleu aussi quand elle couvre la génération, sans rien migrer.
        collection.setCaptureScope(CaptureScope.GENERATION)
        assertTrue(viewModel.state.value.caught)
        assertEquals(CaptureScope.GENERATION, viewModel.state.value.captureScope)
        // Le décocher depuis Bleu le retire de toute la génération, donc de Rouge.
        viewModel.onAction(PokemonAction.ToggleCaught)
        assertFalse(viewModel.state.value.caught)
        collection.setCaptureScope(CaptureScope.GAME)
        games.select(FakeGameDao.RED)
        assertFalse(viewModel.state.value.caught)
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

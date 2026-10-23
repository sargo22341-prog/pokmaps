package org.opensources.pokmaps.ui.pokemon

import androidx.lifecycle.SavedStateHandle
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
import org.opensources.pokmaps.domain.pokemon.CaptureEnvironment
import org.opensources.pokmaps.domain.pokemon.CatchStatus
import org.opensources.pokmaps.domain.pokemon.GenderRatio
import org.opensources.pokmaps.domain.pokemon.GenerationFeature
import org.opensources.pokmaps.domain.pokemon.HeldItem
import org.opensources.pokmaps.domain.pokemon.Machine
import org.opensources.pokmaps.domain.pokemon.MoveNote
import org.opensources.pokmaps.domain.pokemon.MoveTab
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
        FakeGameDao(
            listOf(
                FakeGameDao.RED,
                FakeGameDao.BLUE,
                FakeGameDao.GOLD,
                FakeGameDao.RUBY,
                FakeGameDao.EMERALD,
                FakeGameDao.PLATINUM,
                FakeGameDao.HEARTGOLD,
                FakeGameDao.SOULSILVER
            )
        ),
        GameSettings(dataStore)
    )
    private val collection = CollectionSettings(dataStore)

    private fun viewModel(
        pokemonId: Int,
        failing: Boolean = false,
        unknownLearnMethod: Boolean = false
    ): PokemonViewModel {
        val dao = FakePokemonDao(failing, unknownLearnMethod)
        val repository = PokemonRepository(dao, PokedexRepository(FakePokedexDao()))
        return PokemonViewModel(
            SavedStateHandle(mapOf(PokemonViewModel.POKEMON_ID to pokemonId)),
            ObservePokemonUseCase(games, repository),
            ObserveCollectionUseCase(games, collection),
            UpdateCollectionUseCase(games, collection),
            requests
        )
    }

    @Test
    fun hgssCaptureControlsAndGameChangesKeepEnvironmentsCompatible() = runTest {
        val model = viewModel(PIKACHU)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { model.state.collect {} }
        games.select(FakeGameDao.HEARTGOLD)
        assertTrue(checkNotNull(model.state.value.catch).hgss)
        assertTrue(checkNotNull(model.state.value.catch).probabilities.any { it.first == Ball.HEAVY })
        model.onAction(PokemonAction.ToggleOppositeGender)
        assertTrue(checkNotNull(model.state.value.catch).sameSpeciesOppositeGender)
        model.onAction(PokemonAction.SetCaptureEnvironment(CaptureEnvironment.BUG_CONTEST))
        assertEquals(listOf(Ball.SPORT), model.state.value.catch?.probabilities?.map { it.first })
        games.select(FakeGameDao.PLATINUM)
        assertEquals(CaptureEnvironment.NORMAL, model.state.value.catch?.environment)
        assertFalse(checkNotNull(model.state.value.catch).probabilities.any { it.first == Ball.SPORT })
        model.onAction(PokemonAction.SetCaptureEnvironment(CaptureEnvironment.GREAT_MARSH))
        games.select(FakeGameDao.SOULSILVER)
        assertEquals(CaptureEnvironment.NORMAL, model.state.value.catch?.environment)
        model.onAction(PokemonAction.SetCaptureEnvironment(CaptureEnvironment.HGSS_SAFARI))
        assertEquals(listOf(Ball.SAFARI), model.state.value.catch?.probabilities?.map { it.first })
    }

    @Test
    fun sinnohCaptureContextsRecomputeProbabilities() = runTest {
        val model = viewModel(PIKACHU)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { model.state.collect {} }
        games.select(FakeGameDao.PLATINUM)
        fun probability(ball: Ball): Double = checkNotNull(model.state.value.catch).probabilities.single {
            it.first == ball
        }.second
        assertFalse(model.state.value.failed)
        val quick = probability(Ball.QUICK)
        val dusk = probability(Ball.DUSK)
        model.onAction(PokemonAction.SetElapsedTurns(1))
        assertTrue(quick > probability(Ball.QUICK))
        model.onAction(PokemonAction.ToggleNightOrCave)
        assertTrue(probability(Ball.DUSK) > dusk)
        model.onAction(
            PokemonAction.SetCaptureEnvironment(
                CaptureEnvironment.PAL_PARK
            )
        )
        assertEquals(listOf(Ball.PARK to 1.0), model.state.value.catch?.probabilities)
        games.select(FakeGameDao.RUBY)
        assertFalse(checkNotNull(model.state.value.catch).probabilities.any { it.first == Ball.PARK })
    }

    @Test
    fun startsLoading() {
        assertEquals(PokemonUiState(), viewModel(PIKACHU).state.value)
    }

    @Test
    fun formWritesFollowCollectionScopeAndExposeFailures() = runTest {
        val form = org.opensources.pokmaps.domain.pokemon.PokemonFormTest.form("test", "Forme test", List(6) { 50 })
            .copy(pokemonId = PIKACHU)
        val platinum = FakeGameDao.PLATINUM.copy(forms = mapOf(PIKACHU to listOf(form)))
        val gameRepository = GameRepository(FakeGameDao(listOf(platinum, FakeGameDao.RED)), GameSettings(dataStore))
        val model = PokemonViewModel(
            SavedStateHandle(mapOf(PokemonViewModel.POKEMON_ID to PIKACHU)),
            ObservePokemonUseCase(
                gameRepository,
                PokemonRepository(FakePokemonDao(), PokedexRepository(FakePokedexDao()))
            ),
            ObserveCollectionUseCase(gameRepository, collection),
            UpdateCollectionUseCase(gameRepository, collection),
            requests
        )
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { model.state.collect {} }
        model.onAction(PokemonAction.ToggleForm(form.identifier))
        assertEquals(setOf(form.identifier), model.state.value.caughtForms)
        assertFalse(model.state.value.caught)
        dataStore.writeError = IOException("Écriture impossible")
        model.onAction(PokemonAction.ToggleForm(form.identifier))
        assertTrue(model.state.value.writeFailed)
        assertEquals(setOf(form.identifier), model.state.value.caughtForms)
        dataStore.writeError = null
        model.onAction(PokemonAction.ToggleForm(form.identifier))
        assertTrue(model.state.value.caughtForms.isEmpty())
        assertFalse(model.state.value.writeFailed)
        collection.setFormCaught(setOf(12), form.identifier, true)
        collection.setCaptureScope(CaptureScope.ALL)
        assertEquals(setOf(form.identifier), model.state.value.caughtForms)
        model.onAction(PokemonAction.ToggleForm(form.identifier))
        assertTrue(model.state.value.caughtForms.isEmpty())
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
        // Ni œufs ni tuteurs en 1re génération, mais le Surf de Pokémon Stadium a son onglet et sa mention.
        assertEquals(listOf(MoveTab.LEVEL_UP, MoveTab.MACHINE, MoveTab.TUTOR), red.moveTabs)
        val surf = red.details?.moves(MoveTab.TUTOR)?.single()
        assertEquals(FakePokemonDao.SURF to MoveNote.EXTERNAL_EVENT, surf?.moveId to surf?.note)

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
        assertEquals(listOf(117), gold.details?.eggMoves?.map { it.moveId })
        assertEquals(listOf(87), gold.details?.tutorMoves?.map { it.moveId })
        assertEquals(MoveTab.entries, gold.moveTabs)
        assertEquals(listOf(FakePokemonDao.THUNDER_SHOCK), gold.details?.levelUpMoves?.map { it.moveId })
    }

    @Test
    fun gen3MoveTabsFollowDataAndKeepTheLightBallNote() = runTest {
        val model = viewModel(PIKACHU)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { model.state.collect {} }
        games.select(FakeGameDao.EMERALD)
        assertEquals(listOf(MoveTab.LEVEL_UP, MoveTab.MACHINE, MoveTab.EGG), model.state.value.moveTabs)
        assertEquals(MoveNote.LIGHT_BALL_PARENT, model.state.value.details?.eggMoves?.single()?.note)
        games.select(FakeGameDao.RUBY)
        assertEquals(listOf(MoveTab.LEVEL_UP, MoveTab.MACHINE), model.state.value.moveTabs)
        games.select(FakeGameDao.GOLD)
        assertEquals(MoveTab.entries, model.state.value.moveTabs)
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
    fun johtoCaptureCalculatorFollowsTheBallContext() = runTest {
        val viewModel = viewModel(PIKACHU)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        games.select(FakeGameDao.GOLD)
        viewModel.onAction(PokemonAction.SetCatchLevel(10))
        viewModel.onAction(PokemonAction.SetPlayerLevel(44))
        viewModel.onAction(PokemonAction.ToggleFishing)
        viewModel.onAction(PokemonAction.ToggleLoveBonus)
        val catch = checkNotNull(viewModel.state.value.catch)
        assertEquals(44, catch.playerLevel)
        assertTrue(catch.fishing)
        assertTrue(catch.sameSpeciesAndGender)
        assertEquals(1.0, catch.probabilities.toMap().getValue(Ball.LEVEL), 0.0)
        assertTrue(catch.probabilities.any { it.first == Ball.PARK })
        assertFalse(catch.probabilities.any { it.first == Ball.SAFARI })
    }

    @Test
    fun gen3CaptureContextsAndGenerationSwitch() = runTest {
        games.select(FakeGameDao.RUBY)
        val viewModel = viewModel(PIKACHU)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        val original = checkNotNull(viewModel.state.value.catch).probabilities.toMap()
        viewModel.onAction(PokemonAction.ToggleUnderwater)
        viewModel.onAction(PokemonAction.ToggleAlreadyCaught)
        viewModel.onAction(PokemonAction.SetElapsedTurns(500))
        val catch = checkNotNull(viewModel.state.value.catch)
        assertTrue(catch.underwater)
        assertTrue(catch.alreadyCaught)
        assertEquals(30, catch.elapsedTurns)
        val updated = catch.probabilities.toMap()
        assertTrue(updated.getValue(Ball.DIVE) > original.getValue(Ball.DIVE))
        assertTrue(updated.getValue(Ball.REPEAT) > original.getValue(Ball.REPEAT))
        assertTrue(updated.getValue(Ball.TIMER) > original.getValue(Ball.TIMER))
        assertFalse(Ball.LEVEL in updated)
        viewModel.onAction(PokemonAction.SetElapsedTurns(-1))
        assertEquals(0, viewModel.state.value.catch?.elapsedTurns)
        games.select(FakeGameDao.GOLD)
        assertFalse(checkNotNull(viewModel.state.value.catch).probabilities.any { it.first == Ball.NET })
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
    fun anUnknownLearnMethodIsAnErrorNotAMissingMove() = runTest {
        val viewModel = viewModel(PIKACHU, unknownLearnMethod = true)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        assertTrue(viewModel.state.value.failed)
        assertNull(viewModel.state.value.details)
    }

    @Test
    fun anUnreadableDatabaseIsAnError() = runTest {
        val viewModel = viewModel(PIKACHU, failing = true)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        assertTrue(viewModel.state.value.failed)
        assertNull(viewModel.state.value.details)
    }

    @Test
    fun failedCollectionWritesKeepPreviousValuesAndCanBeRetried() = runTest {
        val model = viewModel(PIKACHU)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { model.state.collect {} }
        dataStore.writeError = IOException("Écriture impossible")
        model.onAction(PokemonAction.ToggleCaught)
        assertTrue(model.state.value.writeFailed)
        assertFalse(model.state.value.caught)
        assertFalse(model.state.value.failed)
        dataStore.writeError = null
        model.onAction(PokemonAction.ToggleCaught)
        assertTrue(model.state.value.caught)
        assertFalse(model.state.value.writeFailed)
        dataStore.writeError = IOException("Écriture impossible")
        model.onAction(PokemonAction.ToggleFavorite)
        assertTrue(model.state.value.writeFailed)
        assertFalse(model.state.value.favorite)
        assertTrue(model.state.value.caught)
        dataStore.writeError = null
        model.onAction(PokemonAction.ToggleFavorite)
        assertTrue(model.state.value.favorite)
        assertFalse(model.state.value.writeFailed)
    }

    @Test
    fun cancelledCollectionWriteDoesNotBecomeAnError() = runTest {
        val model = viewModel(PIKACHU)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { model.state.collect {} }
        dataStore.writeError = CancellationException("Annulation")
        model.onAction(PokemonAction.ToggleCaught)
        model.onAction(PokemonAction.ToggleFavorite)
        assertFalse(model.state.value.writeFailed)
        assertFalse(model.state.value.caught)
        assertFalse(model.state.value.favorite)
    }
}

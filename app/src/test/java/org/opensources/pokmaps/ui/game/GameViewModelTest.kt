package org.opensources.pokmaps.ui.game

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.settings.FakeDataStore
import org.opensources.pokmaps.data.settings.GameSettings
import org.opensources.pokmaps.domain.usecase.ObserveGamesUseCase
import org.opensources.pokmaps.domain.usecase.ObserveSelectedGameUseCase
import org.opensources.pokmaps.domain.usecase.SelectGameUseCase
import org.opensources.pokmaps.ui.MainDispatcherRule

@OptIn(ExperimentalCoroutinesApi::class)
class GameViewModelTest {
    @get:Rule
    val mainDispatcher = MainDispatcherRule()

    private val dataStore = FakeDataStore()

    private fun viewModel(dao: FakeGameDao): GameViewModel {
        val games = GameRepository(dao, GameSettings(dataStore))
        return GameViewModel(ObserveGamesUseCase(games), ObserveSelectedGameUseCase(games), SelectGameUseCase(games))
    }

    @Test
    fun remakesFollowTheOriginalGamesInTheirGeneration() {
        val original = FakeGameDao.RED.copy(generationId = 3, versionId = 7)
        val remake = FakeGameDao.BLUE.copy(generationId = 3, versionId = 10, remakeGenerationId = 1)
        val state = GameUiState(games = listOf(FakeGameDao.RED, remake, original))
        assertEquals(
            listOf(
                GameChoiceRow(1, null, listOf(FakeGameDao.RED)),
                GameChoiceRow(3, null, listOf(original)),
                GameChoiceRow(3, 1, listOf(remake))
            ),
            state.rows
        )
    }

    @Test
    fun startsLoading() {
        assertTrue(viewModel(FakeGameDao()).state.value.loading)
    }

    @Test
    fun firstGameIsSelectedThenTheChosenOneIsRemembered() = runTest {
        val viewModel = viewModel(FakeGameDao())
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        val games = listOf(FakeGameDao.RED, FakeGameDao.BLUE)
        assertEquals(GameUiState(loading = false, games = games, selected = FakeGameDao.RED), viewModel.state.value)
        viewModel.onAction(GameAction.Select(FakeGameDao.BLUE))
        assertEquals(FakeGameDao.BLUE, viewModel.state.value.selected)

        // À la réouverture de l'application, le choix mémorisé est repris.
        val reopened = viewModel(FakeGameDao())
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { reopened.state.collect {} }
        assertEquals(FakeGameDao.BLUE, reopened.state.value.selected)
    }

    @Test
    fun gamesAreGroupedByGeneration() = runTest {
        val viewModel = viewModel(FakeGameDao())
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        assertEquals(
            listOf(GameChoiceRow(1, null, listOf(FakeGameDao.RED, FakeGameDao.BLUE))),
            viewModel.state.value.rows
        )
    }

    @Test
    fun anEmptyGameCatalogIsAnError() = runTest {
        val viewModel = viewModel(FakeGameDao(games = emptyList()))
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        assertEquals(GameUiState(loading = false, failed = true), viewModel.state.value)
    }

    @Test
    fun anUnreadableDatabaseIsAnError() = runTest {
        val viewModel = viewModel(FakeGameDao(failing = true))
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        assertTrue(viewModel.state.value.failed)
        assertFalse(viewModel.state.value.loading)
    }
}

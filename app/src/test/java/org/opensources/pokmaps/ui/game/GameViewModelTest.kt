package org.opensources.pokmaps.ui.game

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
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

    private fun viewModel(dao: FakeGameDao): GameViewModel {
        val games = GameRepository(dao, GameSettings(FakeDataStore()))
        return GameViewModel(ObserveGamesUseCase(games), ObserveSelectedGameUseCase(games), SelectGameUseCase(games))
    }

    @Test
    fun firstGameIsSelectedThenTheChosenOne() = runTest {
        val viewModel = viewModel(FakeGameDao())
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        assertEquals(GameUiState(listOf(FakeGameDao.RED, FakeGameDao.BLUE), FakeGameDao.RED), viewModel.state.value)
        viewModel.select(FakeGameDao.BLUE)
        assertEquals(FakeGameDao.BLUE, viewModel.state.value.selected)
    }

    @Test
    fun noGameKeepsTheEmptyState() = runTest {
        val viewModel = viewModel(FakeGameDao(games = emptyList()))
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        assertEquals(GameUiState(), viewModel.state.value)
    }

    @Test
    fun anUnreadableDatabaseIsAnError() = runTest {
        val viewModel = viewModel(FakeGameDao(failing = true))
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        assertTrue(viewModel.state.value.failed)
    }
}

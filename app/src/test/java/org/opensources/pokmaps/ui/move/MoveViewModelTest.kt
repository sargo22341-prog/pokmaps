package org.opensources.pokmaps.ui.move

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
import org.opensources.pokmaps.data.db.FakeMoveDao
import org.opensources.pokmaps.data.db.FakePokemonDao
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.repository.MoveRepository
import org.opensources.pokmaps.data.settings.FakeDataStore
import org.opensources.pokmaps.data.settings.GameSettings
import org.opensources.pokmaps.domain.pokemon.Machine
import org.opensources.pokmaps.domain.pokemon.MoveEffect
import org.opensources.pokmaps.domain.pokemon.MoveLearner
import org.opensources.pokmaps.domain.usecase.ObserveMoveUseCase
import org.opensources.pokmaps.ui.MainDispatcherRule

@OptIn(ExperimentalCoroutinesApi::class)
class MoveViewModelTest {
    @get:Rule
    val mainDispatcher = MainDispatcherRule()

    private fun viewModel(moveId: Int, failing: Boolean = false): MoveViewModel {
        val games = GameRepository(FakeGameDao(), GameSettings(FakeDataStore()))
        return MoveViewModel(
            SavedStateHandle(mapOf(MoveViewModel.MOVE_ID to moveId)),
            ObserveMoveUseCase(games, MoveRepository(FakeMoveDao(failing)))
        )
    }

    @Test
    fun startsLoading() {
        assertEquals(MoveUiState(), viewModel(FakeMoveDao.THUNDERBOLT).state.value)
    }

    @Test
    fun effectMachineAndLearners() = runTest {
        val viewModel = viewModel(FakeMoveDao.THUNDERBOLT)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        val move = checkNotNull(viewModel.state.value.page?.details)
        assertEquals(MoveEffect(FakeMoveDao.PARALYSIS, FakeMoveDao.CHANCE), move.effect)
        assertEquals(Machine("tm24", "CT24"), move.machine)
        assertEquals(listOf(MoveLearner(FakePokemonDao.PIKACHU, "Pikachu", 26)), move.levelUpLearners)
        assertEquals(listOf(MoveLearner(FakePokemonDao.PIKACHU, "Pikachu", null)), move.machineLearners)
    }

    @Test
    fun aMoveNobodyLearnsHasNoLearnersAndNoChance() = runTest {
        val viewModel = viewModel(FakeMoveDao.GROWL)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        val move = checkNotNull(viewModel.state.value.page?.details)
        assertNull(move.effect.chance)
        assertNull(move.machine)
        assertEquals(emptyList<MoveLearner>(), move.learners)
    }

    @Test
    fun anUnknownMoveIsNotFoundNotAnError() = runTest {
        val viewModel = viewModel(moveId = 999)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        val state = viewModel.state.value
        assertFalse(state.loading)
        assertFalse(state.failed)
        assertNull(state.page?.details)
    }

    @Test
    fun anUnreadableDatabaseIsAnError() = runTest {
        val viewModel = viewModel(FakeMoveDao.THUNDERBOLT, failing = true)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        assertTrue(viewModel.state.value.failed)
        assertNull(viewModel.state.value.page)
    }
}

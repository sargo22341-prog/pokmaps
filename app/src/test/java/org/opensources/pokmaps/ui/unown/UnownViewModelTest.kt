package org.opensources.pokmaps.ui.unown

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
import org.opensources.pokmaps.data.settings.CollectionSettings
import org.opensources.pokmaps.data.settings.FakeDataStore
import org.opensources.pokmaps.data.settings.GameSettings
import org.opensources.pokmaps.data.settings.UnownSettings
import org.opensources.pokmaps.domain.pokedex.CaptureScope
import org.opensources.pokmaps.domain.pokemon.UnownForm
import org.opensources.pokmaps.domain.usecase.UnownUseCase
import org.opensources.pokmaps.ui.MainDispatcherRule

@OptIn(ExperimentalCoroutinesApi::class)
class UnownViewModelTest {
    @get:Rule
    val mainDispatcher = MainDispatcherRule()

    private val dataStore = FakeDataStore()
    private val settings = CollectionSettings(dataStore)
    private val games = GameRepository(
        FakeGameDao(listOf(FakeGameDao.RED, FakeGameDao.GOLD, FakeGameDao.EMERALD, FakeGameDao.FIRERED)),
        GameSettings(dataStore)
    )

    private fun viewModel(failing: Boolean = false): UnownViewModel = UnownViewModel(
        UnownUseCase(games, UnownSettings(if (failing) FakeDataStore(true) else dataStore), settings)
    )

    @Test
    fun generationOneIsEmptyNotFailed() = runTest {
        val viewModel = viewModel()
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        assertTrue(checkNotNull(viewModel.state.value.collection).forms.isEmpty())
        assertFalse(viewModel.state.value.failed)
    }

    @Test
    fun remakePunctuationPersistsAndHoennStaysEmpty() = runTest {
        games.select(FakeGameDao.FIRERED)
        val model = viewModel()
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { model.state.collect {} }
        assertEquals(28, model.state.value.collection?.forms?.size)
        model.toggle(UnownForm.QUESTION)
        model.toggle(UnownForm.EXCLAMATION)
        val punctuation = setOf(UnownForm.QUESTION, UnownForm.EXCLAMATION)
        assertEquals(punctuation, model.state.value.collection?.caught)
        settings.setCaptureScope(CaptureScope.ALL)
        games.select(FakeGameDao.EMERALD)
        assertTrue(checkNotNull(model.state.value.collection).forms.isEmpty())
        assertTrue(checkNotNull(model.state.value.collection).caught.isEmpty())
        assertFalse(model.state.value.failed)
        games.select(FakeGameDao.GOLD)
        assertTrue(checkNotNull(model.state.value.collection).caught.isEmpty())
        games.select(FakeGameDao.FIRERED)
        assertEquals(punctuation, model.state.value.collection?.caught)
    }

    @Test
    fun readFailureIsVisible() = runTest {
        val viewModel = viewModel(true)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        assertTrue(viewModel.state.value.failed)
        assertFalse(viewModel.state.value.loading)
    }

    @Test
    fun formsPersistAndRespectScopeWithoutChangingSpeciesCaptures() = runTest {
        games.select(FakeGameDao.GOLD)
        val viewModel = viewModel()
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        viewModel.toggle(UnownForm.B)
        assertEquals(setOf(UnownForm.B), viewModel.state.value.collection?.caught)
        games.select(FakeGameDao.RED)
        assertTrue(checkNotNull(viewModel.state.value.collection).caught.isEmpty())
        settings.setCaptureScope(CaptureScope.ALL)
        games.select(FakeGameDao.GOLD)
        assertEquals(setOf(UnownForm.B), viewModel.state.value.collection?.caught)
        viewModel.toggle(UnownForm.B)
        assertTrue(checkNotNull(viewModel.state.value.collection).caught.isEmpty())
    }
}

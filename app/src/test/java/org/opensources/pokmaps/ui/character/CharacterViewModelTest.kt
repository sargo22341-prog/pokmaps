package org.opensources.pokmaps.ui.character

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
import org.opensources.pokmaps.data.db.FakeMapDao
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.repository.MapRepository
import org.opensources.pokmaps.data.settings.FakeDataStore
import org.opensources.pokmaps.data.settings.GameSettings
import org.opensources.pokmaps.domain.map.NpcOffer
import org.opensources.pokmaps.domain.usecase.MapRequest
import org.opensources.pokmaps.domain.usecase.MapRequests
import org.opensources.pokmaps.domain.usecase.ObserveCharacterPageUseCase
import org.opensources.pokmaps.ui.MainDispatcherRule

@OptIn(ExperimentalCoroutinesApi::class)
class CharacterViewModelTest {
    @get:Rule
    val mainDispatcher = MainDispatcherRule()

    private val requests = MapRequests()

    private fun viewModel(objectId: Int, failing: Boolean = false): CharacterViewModel {
        val games = GameRepository(FakeGameDao(), GameSettings(FakeDataStore()))
        return CharacterViewModel(
            SavedStateHandle(mapOf(CharacterViewModel.CHARACTER to objectId)),
            ObserveCharacterPageUseCase(games, MapRepository(FakeMapDao(failing))),
            requests
        )
    }

    @Test
    fun startsLoading() {
        assertEquals(CharacterUiState(), viewModel(FakeMapDao.TRAINER).state.value)
    }

    @Test
    fun trainerPageShowsItsParty() = runTest {
        val viewModel = viewModel(FakeMapDao.TRAINER)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        val page = checkNotNull(viewModel.state.value.page)
        assertEquals(listOf("Rattata"), page.party.map { it.name })
        assertTrue(page.offers.isEmpty())
        viewModel.onAction(CharacterAction.ShowOnMap)
        assertEquals(MapRequest.FocusObject(FakeMapDao.TRAINER), requests.pending.value)
    }

    @Test
    fun clerkPageShowsItsSales() = runTest {
        val viewModel = viewModel(FakeMapDao.CLERK)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        val sale = checkNotNull(viewModel.state.value.page).offers.single() as NpcOffer.Sale
        assertEquals("Potion", sale.item.name)
        assertEquals(300, sale.price)
    }

    @Test
    fun anUnknownCharacterIsNotFoundNotAnError() = runTest {
        val viewModel = viewModel(objectId = 999)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        assertNull(viewModel.state.value.page)
        assertFalse(viewModel.state.value.failed)
        assertFalse(viewModel.state.value.loading)
    }

    @Test
    fun anUnreadableDatabaseIsAnError() = runTest {
        val viewModel = viewModel(FakeMapDao.TRAINER, failing = true)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        assertTrue(viewModel.state.value.failed)
    }
}

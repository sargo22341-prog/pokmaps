package org.opensources.pokmaps.ui.item

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
import org.opensources.pokmaps.domain.usecase.MapRequest
import org.opensources.pokmaps.domain.usecase.MapRequests
import org.opensources.pokmaps.domain.usecase.ObserveItemPageUseCase
import org.opensources.pokmaps.ui.MainDispatcherRule

@OptIn(ExperimentalCoroutinesApi::class)
class ItemViewModelTest {
    @get:Rule
    val mainDispatcher = MainDispatcherRule()

    private val requests = MapRequests()

    private fun viewModel(identifier: String, failing: Boolean = false): ItemViewModel {
        val games = GameRepository(FakeGameDao(), GameSettings(FakeDataStore()))
        return ItemViewModel(
            SavedStateHandle(mapOf(ItemViewModel.ITEM to identifier)),
            ObserveItemPageUseCase(games, MapRepository(FakeMapDao(failing))),
            requests
        )
    }

    @Test
    fun startsLoading() {
        assertEquals(ItemUiState(), viewModel("potion").state.value)
    }

    @Test
    fun itemPageListsWhereToFindAndBuyIt() = runTest {
        val viewModel = viewModel("potion")
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        val page = checkNotNull(viewModel.state.value.page)
        assertEquals("Soigne 20 PV.", page.details?.description)
        assertEquals(listOf(FakeMapDao.ITEM), page.found.map { it.obj.id })
        assertEquals(listOf(300), page.sold.map { it.price })
        viewModel.onAction(ItemAction.ShowOnMap(FakeMapDao.CLERK))
        assertEquals(MapRequest.FocusObject(FakeMapDao.CLERK), requests.pending.value)
    }

    @Test
    fun anUnknownItemIsNotFoundNotAnError() = runTest {
        val viewModel = viewModel("master-ball")
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        val state = viewModel.state.value
        assertNull(state.page)
        assertFalse(state.loading)
        assertFalse(state.failed)
    }

    @Test
    fun anUnreadableDatabaseIsAnError() = runTest {
        val viewModel = viewModel("potion", failing = true)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        assertTrue(viewModel.state.value.failed)
        assertNull(viewModel.state.value.page)
    }
}

package org.opensources.pokmaps.ui.place

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
import org.opensources.pokmaps.data.settings.CollectionSettings
import org.opensources.pokmaps.data.settings.FakeDataStore
import org.opensources.pokmaps.data.settings.GameSettings
import org.opensources.pokmaps.domain.map.CharacterRole
import org.opensources.pokmaps.domain.usecase.MapRequest
import org.opensources.pokmaps.domain.usecase.MapRequests
import org.opensources.pokmaps.domain.usecase.ObserveCollectionUseCase
import org.opensources.pokmaps.domain.usecase.ObservePlacePageUseCase
import org.opensources.pokmaps.ui.MainDispatcherRule

@OptIn(ExperimentalCoroutinesApi::class)
class PlaceViewModelTest {
    @get:Rule
    val mainDispatcher = MainDispatcherRule()

    private val requests = MapRequests()
    private val collection = CollectionSettings(FakeDataStore())

    private fun viewModel(identifier: String, failing: Boolean = false, composite: Boolean = false): PlaceViewModel {
        val games = GameRepository(FakeGameDao(), GameSettings(FakeDataStore()))
        return PlaceViewModel(
            SavedStateHandle(mapOf(PlaceViewModel.PLACE to identifier)),
            ObservePlacePageUseCase(games, MapRepository(FakeMapDao(failing, includeCompositeInterior = composite))),
            ObserveCollectionUseCase(games, collection),
            requests
        )
    }

    @Test
    fun startsLoading() {
        assertEquals(PlaceUiState(), viewModel("route-1").state.value)
    }

    @Test
    fun aComposedFloorListsAllItsRoomsWithoutCallingThemCities() = runTest {
        val plan = viewModel("pokemon-lab-plan", composite = true)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { plan.state.collect {} }
        val page = checkNotNull(plan.state.value.page)
        assertFalse(page.outdoor)
        assertEquals(1, page.encounters.size)
        assertTrue(page.characters.any { it.id == FakeMapDao.CLERK })
        assertTrue(page.characters.any { it.id == FakeMapDao.REVIVER })
        val room = viewModel("viridian-mart", composite = true)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { room.state.collect {} }
        assertFalse(checkNotNull(room.state.value.page).outdoor)
    }

    @Test
    fun placePageGroupsItsEncountersAndListsItsContent() = runTest {
        val viewModel = viewModel("route-1")
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        val state = viewModel.state.value
        val page = checkNotNull(state.page)
        assertEquals(listOf("Marche"), state.encounterGroups.map { it.methodName })
        assertEquals(listOf(FakeMapDao.ITEM), page.items.map { it.id })
        assertEquals(listOf(FakeMapDao.TRAINER), page.characters.map { it.id })
        viewModel.onAction(PlaceAction.ShowPlace)
        assertEquals(MapRequest.OpenPlace("route-1"), requests.pending.value)
    }

    @Test
    fun theRouteSaysWhichWildPokemonAreCaught() = runTest {
        val viewModel = viewModel("route-1")
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        assertEquals(setOf(FakeMapDao.PIDGEY), viewModel.state.value.wildIds)
        assertEquals(0, viewModel.state.value.caughtWild)
        collection.setCaught(setOf(FakeGameDao.RED.versionId), FakeMapDao.PIDGEY, caught = true)
        assertEquals(1, viewModel.state.value.caughtWild)
        assertTrue(FakeMapDao.PIDGEY in viewModel.state.value.caught)
    }

    @Test
    fun charactersOfAPlaceShowWhatTheyDo() = runTest {
        val viewModel = viewModel("pokemon-lab")
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        val page = checkNotNull(viewModel.state.value.page)
        assertEquals(
            listOf(FakeMapDao.FOSSIL, FakeMapDao.REVIVER, FakeMapDao.NURSE, FakeMapDao.PRIZES),
            page.characters.map { it.id }
        )
        assertEquals(
            listOf(
                listOf(CharacterRole.OBJECT, CharacterRole.GIFT),
                listOf(CharacterRole.CHARACTER, CharacterRole.FOSSIL),
                listOf(CharacterRole.CHARACTER, CharacterRole.HEAL),
                listOf(CharacterRole.PRIZES)
            ),
            page.characters.map { page.rolesOf(it) }
        )
        assertEquals("Kabuto", page.fossilUses.getValue("dome-fossil").pokemonName)
        assertTrue(viewModel.state.value.wildIds.isEmpty())
    }

    @Test
    fun aPlaceWithoutEncounterHasNoGroup() = runTest {
        val viewModel = viewModel("viridian-mart")
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        assertTrue(viewModel.state.value.encounterGroups.isEmpty())
        assertEquals(listOf(FakeMapDao.CLERK), checkNotNull(viewModel.state.value.page).characters.map { it.id })
    }

    @Test
    fun anUnknownPlaceIsNotFoundNotAnError() = runTest {
        val viewModel = viewModel("cinnabar-island")
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        assertNull(viewModel.state.value.page)
        assertFalse(viewModel.state.value.failed)
        assertFalse(viewModel.state.value.loading)
    }

    @Test
    fun anUnreadableDatabaseIsAnError() = runTest {
        val viewModel = viewModel("route-1", failing = true)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        assertTrue(viewModel.state.value.failed)
    }
}

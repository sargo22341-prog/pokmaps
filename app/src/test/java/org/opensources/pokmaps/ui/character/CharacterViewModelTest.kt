package org.opensources.pokmaps.ui.character

import androidx.lifecycle.SavedStateHandle
import java.io.IOException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
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
import org.opensources.pokmaps.data.settings.RivalSettings
import org.opensources.pokmaps.domain.map.CharacterRole
import org.opensources.pokmaps.domain.map.NpcOffer
import org.opensources.pokmaps.domain.map.RivalChoice
import org.opensources.pokmaps.domain.usecase.MapRequest
import org.opensources.pokmaps.domain.usecase.MapRequests
import org.opensources.pokmaps.domain.usecase.ObserveCharacterPageUseCase
import org.opensources.pokmaps.domain.usecase.RivalChoiceUseCase
import org.opensources.pokmaps.ui.MainDispatcherRule

@OptIn(ExperimentalCoroutinesApi::class)
class CharacterViewModelTest {
    @get:Rule
    val mainDispatcher = MainDispatcherRule()

    private val requests = MapRequests()

    private fun viewModel(
        objectId: Int,
        failing: Boolean = false,
        blue: Boolean = false,
        dataStore: FakeDataStore = FakeDataStore()
    ): CharacterViewModel {
        val games = GameRepository(FakeGameDao(), GameSettings(dataStore))
        if (blue) runBlocking { games.select(FakeGameDao.BLUE) }
        return CharacterViewModel(
            SavedStateHandle(mapOf(CharacterViewModel.CHARACTER to objectId)),
            ObserveCharacterPageUseCase(games, MapRepository(FakeMapDao(failing), Dispatchers.Unconfined)),
            RivalChoiceUseCase(games, RivalSettings(dataStore)),
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
        assertEquals(listOf(listOf("Rattata")), page.teams.map { team -> team.members.map { it.name } })
        assertEquals(null, page.teams.single().variant)
        assertEquals(page.teams, viewModel.state.value.teams.shown)
        assertTrue(page.offers.isEmpty())
        viewModel.onAction(CharacterAction.ShowOnMap)
        assertEquals(MapRequest.FocusObject(FakeMapDao.TRAINER), requests.pending.value)
    }

    @Test
    fun theRivalChoiceIsRememberedForTheGame() = runTest {
        val dataStore = FakeDataStore()
        val viewModel = viewModel(FakeMapDao.TRAINER, dataStore = dataStore)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        viewModel.onAction(CharacterAction.ChooseRival(RivalChoice(starterId = 4)))
        assertEquals(RivalChoice(starterId = 4), viewModel.state.value.rivalChoice)
        assertEquals(RivalChoice(starterId = 4), viewModel.state.value.teams.choice)
        assertFalse(viewModel.state.value.choiceFailed)
        val other = viewModel(FakeMapDao.TRAINER, dataStore = dataStore)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { other.state.collect {} }
        assertEquals(RivalChoice(starterId = 4), other.state.value.rivalChoice)
    }

    @Test
    fun anUnsavedRivalChoiceIsShownAsAnError() = runTest {
        val dataStore = FakeDataStore()
        val viewModel = viewModel(FakeMapDao.TRAINER, dataStore = dataStore)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        dataStore.writeError = IOException("Disque plein")
        viewModel.onAction(CharacterAction.ChooseRival(RivalChoice(starterId = 4)))
        assertTrue(viewModel.state.value.choiceFailed)
        assertEquals(RivalChoice(), viewModel.state.value.rivalChoice)
        assertNotNull(viewModel.state.value.page)
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
    fun aFossilSaysWhatItBecomesAndWhereToReviveIt() = runTest {
        val viewModel = viewModel(FakeMapDao.FOSSIL)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        val page = checkNotNull(viewModel.state.value.page)
        val gift = page.offers.single() as NpcOffer.GiftItem
        val use = checkNotNull(page.fossilUses[gift.item.identifier])
        assertEquals("Kabuto", use.pokemonName)
        assertEquals(30, use.level)
        assertEquals(FakeMapDao.REVIVER, use.reviver.id)
        assertEquals(listOf(CharacterRole.OBJECT, CharacterRole.GIFT), page.roles)
        viewModel.onAction(CharacterAction.ShowObject(use.reviver.id))
        assertEquals(MapRequest.FocusObject(FakeMapDao.REVIVER), requests.pending.value)
    }

    @Test
    fun theScientistRevivesFossilsAndTheNurseHeals() = runTest {
        val reviver = viewModel(FakeMapDao.REVIVER)
        val nurse = viewModel(FakeMapDao.NURSE)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { reviver.state.collect {} }
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { nurse.state.collect {} }
        val revival = checkNotNull(reviver.state.value.page).offers.single() as NpcOffer.FossilRevival
        assertEquals(listOf("Fossile Dôme", "Kabuto"), listOf(revival.fossil.name, revival.name))
        assertEquals(listOf(CharacterRole.CHARACTER, CharacterRole.HEAL), checkNotNull(nurse.state.value.page).roles)
    }

    @Test
    fun gameCornerPrizesDependOnTheVersion() = runTest {
        val red = viewModel(FakeMapDao.PRIZES)
        val blue = viewModel(FakeMapDao.PRIZES, blue = true)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { red.state.collect {} }
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { blue.state.collect {} }
        val redPrize = checkNotNull(red.state.value.page).offers.single() as NpcOffer.PrizePokemon
        val bluePrize = checkNotNull(blue.state.value.page).offers.single() as NpcOffer.PrizePokemon
        assertEquals(FakeMapDao.RED_ABRA_COINS, redPrize.coins)
        assertEquals(FakeMapDao.BLUE_ABRA_COINS, bluePrize.coins)
        assertEquals(listOf(CharacterRole.PRIZES), checkNotNull(red.state.value.page).roles)
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

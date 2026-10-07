package org.opensources.pokmaps.ui.settings

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.opensources.pokmaps.data.settings.DisplaySettings
import org.opensources.pokmaps.data.settings.FakeDataStore
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.domain.usecase.DisplaySettingsUseCase
import org.opensources.pokmaps.ui.MainDispatcherRule

@OptIn(ExperimentalCoroutinesApi::class)
class SettingsViewModelTest {
    @get:Rule
    val mainDispatcher = MainDispatcherRule()

    private fun viewModel(failing: Boolean = false) =
        SettingsViewModel(DisplaySettingsUseCase(DisplaySettings(FakeDataStore(failing))))

    @Test
    fun defaultsBeforeAnyChange() = runTest {
        val viewModel = viewModel()
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        val state = viewModel.state.value
        assertEquals(SettingsUiState(animatedPlaces = SpritePlace.DEFAULT_ANIMATED), state)
        assertTrue(state.partlyAnimated)
        assertFalse(state.allAnimated)
    }

    @Test
    fun theMainSwitchAnimatesOrFreezesEveryPlace() = runTest {
        val viewModel = viewModel()
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        viewModel.onAction(SettingsAction.SetAllAnimated(true))
        assertTrue(viewModel.state.value.allAnimated)
        viewModel.onAction(SettingsAction.SetAllAnimated(false))
        assertEquals(emptySet<SpritePlace>(), viewModel.state.value.animatedPlaces)
        assertFalse(viewModel.state.value.partlyAnimated)
    }

    @Test
    fun eachPlaceIsAnimatedOnItsOwn() = runTest {
        val viewModel = viewModel()
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        // Exemple demandé : fixes sur la carte, la liste et le Pokédex, animés sur les lignes d'évolution.
        viewModel.onAction(SettingsAction.SetAllAnimated(false))
        viewModel.onAction(SettingsAction.SetAnimated(SpritePlace.EVOLUTIONS, true))
        assertEquals(setOf(SpritePlace.EVOLUTIONS), viewModel.state.value.animatedPlaces)
        viewModel.onAction(SettingsAction.SetAnimated(SpritePlace.MAP, true))
        viewModel.onAction(SettingsAction.SetAnimated(SpritePlace.EVOLUTIONS, false))
        assertEquals(setOf(SpritePlace.MAP), viewModel.state.value.animatedPlaces)
    }

    @Test
    fun unreadableSettingsAreAnErrorWithDefaults() = runTest {
        val viewModel = viewModel(failing = true)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        assertEquals(SettingsUiState(failed = true), viewModel.state.value)
    }
}

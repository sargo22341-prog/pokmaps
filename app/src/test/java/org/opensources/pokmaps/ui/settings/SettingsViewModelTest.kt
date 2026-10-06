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
        assertEquals(SettingsUiState(animatedSprites = true, mapAnimatedSprites = false), viewModel.state.value)
    }

    @Test
    fun actionsChangeTheSettings() = runTest {
        val viewModel = viewModel()
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        viewModel.onAction(SettingsAction.SetAnimatedSprites(false))
        viewModel.onAction(SettingsAction.SetMapAnimatedSprites(true))
        assertFalse(viewModel.state.value.animatedSprites)
        assertTrue(viewModel.state.value.mapAnimatedSprites)
    }

    @Test
    fun unreadableSettingsAreAnErrorWithDefaults() = runTest {
        val viewModel = viewModel(failing = true)
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.state.collect {} }
        assertEquals(SettingsUiState(failed = true), viewModel.state.value)
    }
}

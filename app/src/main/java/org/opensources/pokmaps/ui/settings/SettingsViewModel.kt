package org.opensources.pokmaps.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import org.opensources.pokmaps.domain.usecase.DisplaySettingsUseCase
import org.opensources.pokmaps.ui.common.STOP_TIMEOUT_MS

data class SettingsUiState(
    val animatedSprites: Boolean = true,
    val mapAnimatedSprites: Boolean = false,
    /** Réglages illisibles : les valeurs par défaut sont affichées. */
    val failed: Boolean = false
)

/** Intentions de l'écran Réglages. */
sealed interface SettingsAction {
    data class SetAnimatedSprites(val enabled: Boolean) : SettingsAction

    data class SetMapAnimatedSprites(val enabled: Boolean) : SettingsAction
}

/** Réglages de l'application (écran Réglages, et sprites animés lus partout). */
@HiltViewModel
class SettingsViewModel @Inject constructor(private val settings: DisplaySettingsUseCase) : ViewModel() {
    val state: StateFlow<SettingsUiState> = combine(settings.animatedSprites, settings.mapAnimatedSprites) { app, map ->
        SettingsUiState(animatedSprites = app, mapAnimatedSprites = map)
    }.catch { emit(SettingsUiState(failed = true)) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(STOP_TIMEOUT_MS), SettingsUiState())

    fun onAction(action: SettingsAction) {
        viewModelScope.launch {
            when (action) {
                is SettingsAction.SetAnimatedSprites -> settings.setAnimatedSprites(action.enabled)
                is SettingsAction.SetMapAnimatedSprites -> settings.setMapAnimatedSprites(action.enabled)
            }
        }
    }
}

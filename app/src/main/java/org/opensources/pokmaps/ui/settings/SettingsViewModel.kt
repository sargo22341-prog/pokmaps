package org.opensources.pokmaps.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import org.opensources.pokmaps.data.settings.DisplaySettings
import org.opensources.pokmaps.ui.game.STOP_TIMEOUT_MS

data class SettingsUiState(val animatedSprites: Boolean = true)

/** Réglages de l'application (écran Réglages, et sprites animés lus partout). */
@HiltViewModel
class SettingsViewModel @Inject constructor(private val settings: DisplaySettings) : ViewModel() {
    val state: StateFlow<SettingsUiState> = settings.animatedSprites
        .map { SettingsUiState(animatedSprites = it) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(STOP_TIMEOUT_MS), SettingsUiState())

    fun setAnimatedSprites(enabled: Boolean) {
        viewModelScope.launch { settings.setAnimatedSprites(enabled) }
    }
}

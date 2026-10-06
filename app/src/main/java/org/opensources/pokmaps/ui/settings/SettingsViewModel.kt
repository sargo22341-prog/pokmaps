package org.opensources.pokmaps.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import org.opensources.pokmaps.data.settings.DisplaySettings
import org.opensources.pokmaps.ui.game.STOP_TIMEOUT_MS

data class SettingsUiState(val animatedSprites: Boolean = true, val mapAnimatedSprites: Boolean = false)

/** Réglages de l'application (écran Réglages, et sprites animés lus partout). */
@HiltViewModel
class SettingsViewModel @Inject constructor(private val settings: DisplaySettings) : ViewModel() {
    val state: StateFlow<SettingsUiState> = combine(settings.animatedSprites, settings.mapAnimatedSprites) { app, map ->
        SettingsUiState(animatedSprites = app, mapAnimatedSprites = map)
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(STOP_TIMEOUT_MS), SettingsUiState())

    fun setAnimatedSprites(enabled: Boolean) {
        viewModelScope.launch { settings.setAnimatedSprites(enabled) }
    }

    fun setMapAnimatedSprites(enabled: Boolean) {
        viewModelScope.launch { settings.setMapAnimatedSprites(enabled) }
    }
}

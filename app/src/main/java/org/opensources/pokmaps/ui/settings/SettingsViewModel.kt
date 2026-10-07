package org.opensources.pokmaps.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.domain.usecase.DisplaySettingsUseCase
import org.opensources.pokmaps.ui.common.STOP_TIMEOUT_MS

data class SettingsUiState(
    /** Endroits où les sprites des Pokémon sont animés. */
    val animatedPlaces: Set<SpritePlace> = SpritePlace.DEFAULT_ANIMATED,
    /** Réglages illisibles : les valeurs par défaut sont affichées. */
    val failed: Boolean = false
) {
    /** Sprites animés partout (interrupteur général). */
    val allAnimated: Boolean get() = animatedPlaces.containsAll(SpritePlace.entries)

    /** Animés à certains endroits seulement. */
    val partlyAnimated: Boolean get() = animatedPlaces.isNotEmpty() && !allAnimated
}

/** Intentions de l'écran Réglages. */
sealed interface SettingsAction {
    /** Anime ou fige les sprites partout. */
    data class SetAllAnimated(val enabled: Boolean) : SettingsAction

    data class SetAnimated(val place: SpritePlace, val enabled: Boolean) : SettingsAction
}

/** Réglages de l'application (écran Réglages, et sprites animés lus partout). */
@HiltViewModel
class SettingsViewModel @Inject constructor(private val settings: DisplaySettingsUseCase) : ViewModel() {
    val state: StateFlow<SettingsUiState> = settings.animatedPlaces
        .map { SettingsUiState(animatedPlaces = it) }
        .catch { emit(SettingsUiState(failed = true)) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(STOP_TIMEOUT_MS), SettingsUiState())

    fun onAction(action: SettingsAction) {
        viewModelScope.launch {
            when (action) {
                is SettingsAction.SetAllAnimated -> settings.setAllAnimated(action.enabled)
                is SettingsAction.SetAnimated -> settings.setAnimated(action.place, action.enabled)
            }
        }
    }
}

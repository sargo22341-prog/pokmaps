package org.opensources.pokmaps.ui.guide

import androidx.lifecycle.ViewModel
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import org.opensources.pokmaps.domain.guide.FriendshipEvent
import org.opensources.pokmaps.domain.guide.FriendshipRules

data class FriendshipUiState(
    val value: Int = 70,
    val event: FriendshipEvent = FriendshipEvent.LEVEL,
    val rules: FriendshipRules = FriendshipRules.GOLD_SILVER,
    val sootheBell: Boolean = false,
    val luxuryBall: Boolean = false,
    val capturePlace: Boolean = false
) {
    val result: Int = rules.apply(event, value, sootheBell, luxuryBall, capturePlace)
    val delta: Int = result - value
    val events: List<FriendshipEvent> = rules.events
}

sealed interface FriendshipAction {
    data class Value(val value: Int) : FriendshipAction
    data class Event(val event: FriendshipEvent) : FriendshipAction
    data class Rules(val rules: FriendshipRules) : FriendshipAction
    data class SootheBell(val enabled: Boolean) : FriendshipAction
    data class LuxuryBall(val enabled: Boolean) : FriendshipAction
    data class CapturePlace(val enabled: Boolean) : FriendshipAction
}

@HiltViewModel
class FriendshipViewModel @Inject constructor() : ViewModel() {
    private val mutableState = MutableStateFlow(FriendshipUiState())
    val state: StateFlow<FriendshipUiState> = mutableState.asStateFlow()

    fun onAction(action: FriendshipAction) {
        mutableState.update { state ->
            when (action) {
                is FriendshipAction.Value -> state.copy(value = action.value.coerceIn(0, 255))

                is FriendshipAction.Event -> if (action.event in
                    state.events
                ) {
                    state.copy(event = action.event)
                } else {
                    state
                }

                is FriendshipAction.Rules -> FriendshipUiState(
                    value = state.value,
                    rules = action.rules,
                    event = state.event.takeIf { it in action.rules.events } ?: FriendshipEvent.LEVEL
                )

                is FriendshipAction.SootheBell -> state.copy(sootheBell = action.enabled)

                is FriendshipAction.LuxuryBall -> state.copy(luxuryBall = action.enabled)

                is FriendshipAction.CapturePlace -> state.copy(capturePlace = action.enabled)
            }
        }
    }
}

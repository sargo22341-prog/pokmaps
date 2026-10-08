package org.opensources.pokmaps.ui.guide

import androidx.lifecycle.ViewModel
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import org.opensources.pokmaps.domain.guide.FriendshipEvent

data class FriendshipUiState(
    val value: Int = 70,
    val event: FriendshipEvent = FriendshipEvent.LEVEL,
    val crystal: Boolean = false
) {
    val result: Int = event.apply(value)
    val delta: Int = result - value
    val events: List<FriendshipEvent> = FriendshipEvent.entries.filter {
        crystal || it != FriendshipEvent.LEVEL_AT_CAPTURE_PLACE
    }
}

sealed interface FriendshipAction {
    data class Value(val value: Int) : FriendshipAction
    data class Event(val event: FriendshipEvent) : FriendshipAction
    data class Crystal(val enabled: Boolean) : FriendshipAction
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

                is FriendshipAction.Crystal -> state.copy(
                    crystal = action.enabled,
                    event = if (!action.enabled && state.event == FriendshipEvent.LEVEL_AT_CAPTURE_PLACE) {
                        FriendshipEvent.LEVEL
                    } else {
                        state.event
                    }
                )
            }
        }
    }
}

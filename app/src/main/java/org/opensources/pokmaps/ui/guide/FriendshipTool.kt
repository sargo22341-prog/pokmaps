package org.opensources.pokmaps.ui.guide

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlin.math.roundToInt
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.FriendshipEvent
import org.opensources.pokmaps.domain.guide.FriendshipRules

@Composable
internal fun FriendshipRoute(rules: FriendshipRules, viewModel: FriendshipViewModel = hiltViewModel()) {
    LaunchedEffect(rules) { viewModel.onAction(FriendshipAction.Rules(rules)) }
    val state by viewModel.state.collectAsStateWithLifecycle()
    FriendshipTool(state, viewModel::onAction)
}

@Composable
internal fun FriendshipTool(state: FriendshipUiState, onAction: (FriendshipAction) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(stringResource(R.string.friendship_tool), style = MaterialTheme.typography.titleLarge)
        Text(
            stringResource(
                if (state.rules.modern) R.string.friendship_gba_simulation else R.string.friendship_simulation
            ),
            style = MaterialTheme.typography.bodySmall
        )
        FriendshipValue(state, onAction)
        Column {
            OutlinedButton(onClick = { expanded = true }, modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(state.event.label(state.rules == FriendshipRules.SINNOH)))
            }
            DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                state.events.forEach { event ->
                    DropdownMenuItem(text = {
                        Text(stringResource(event.label(state.rules == FriendshipRules.SINNOH)))
                    }, onClick = {
                        expanded = false
                        onAction(FriendshipAction.Event(event))
                    })
                }
            }
        }
        Text(
            stringResource(R.string.friendship_result, state.result, state.delta),
            style = MaterialTheme.typography.titleMedium
        )
        Text(stringResource(R.string.friendship_bands, state.event.low, state.event.medium, state.event.high))
        if (state.rules.modern) GbaFriendshipOptions(state, onAction)
        Text(
            stringResource(if (state.rules.modern) R.string.friendship_gba_random else R.string.friendship_random),
            style = MaterialTheme.typography.bodySmall
        )
    }
}

@Composable
private fun FriendshipValue(state: FriendshipUiState, onAction: (FriendshipAction) -> Unit) {
    Text(stringResource(R.string.friendship_value, state.value))
    Slider(
        value = state.value.toFloat(),
        valueRange = 0f..255f,
        onValueChange = { onAction(FriendshipAction.Value(it.roundToInt())) }
    )
    Row {
        listOf(70, 120, 200, 220).forEach { value ->
            TextButton(onClick = {
                onAction(FriendshipAction.Value(value))
            }) { Text(stringResource(R.string.friendship_preset, value)) }
        }
    }
}

private fun FriendshipEvent.label(sinnoh: Boolean): Int = when (this) {
    FriendshipEvent.LEVEL -> R.string.friendship_level
    FriendshipEvent.VITAMIN -> R.string.friendship_vitamin
    FriendshipEvent.X_ITEM -> R.string.friendship_x_item
    FriendshipEvent.GYM_BATTLE -> R.string.friendship_gym
    FriendshipEvent.LEARN_MOVE -> R.string.friendship_move
    FriendshipEvent.FAINT -> R.string.friendship_faint
    FriendshipEvent.POISON_FAINT -> if (sinnoh) R.string.friendship_sinnoh_poison else R.string.friendship_poison
    FriendshipEvent.STRONG_ENEMY_FAINT -> R.string.friendship_strong
    FriendshipEvent.BITTER_POWDER -> R.string.friendship_powder
    FriendshipEvent.ENERGY_ROOT -> R.string.friendship_root
    FriendshipEvent.REVIVAL_HERB -> R.string.friendship_herb
    FriendshipEvent.GROOMING -> R.string.friendship_grooming
    FriendshipEvent.LEVEL_AT_CAPTURE_PLACE -> R.string.friendship_home
    FriendshipEvent.WALKING -> R.string.friendship_walking
    FriendshipEvent.MASSAGE -> R.string.friendship_massage
    FriendshipEvent.EV_BERRY -> R.string.friendship_ev_berry
    FriendshipEvent.SPA -> R.string.friendship_spa
    FriendshipEvent.SPA_MEDIUM -> R.string.friendship_spa_medium
    FriendshipEvent.SPA_LARGE -> R.string.friendship_spa_large
    FriendshipEvent.CONTEST -> R.string.friendship_contest
}

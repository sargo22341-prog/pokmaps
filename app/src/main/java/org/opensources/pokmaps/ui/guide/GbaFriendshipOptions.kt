package org.opensources.pokmaps.ui.guide

import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.selection.toggleable
import androidx.compose.material3.Checkbox
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.FriendshipRules

@Composable
internal fun GbaFriendshipOptions(state: FriendshipUiState, onAction: (FriendshipAction) -> Unit) {
    FriendshipOption(state.sootheBell, R.string.friendship_soothe_bell) { onAction(FriendshipAction.SootheBell(it)) }
    FriendshipOption(state.luxuryBall, R.string.friendship_luxury_ball) { onAction(FriendshipAction.LuxuryBall(it)) }
    FriendshipOption(
        state.capturePlace,
        if (state.rules.ds) {
            R.string.friendship_egg_place
        } else {
            R.string.friendship_capture_place
        }
    ) {
        onAction(FriendshipAction.CapturePlace(it))
    }
    Text(
        stringResource(
            if (state.rules == FriendshipRules.HEARTGOLD_SOULSILVER) {
                R.string.friendship_hgss_note
            } else if (state.rules.ds) {
                R.string.friendship_sinnoh_note
            } else {
                R.string.friendship_gba_note
            }
        )
    )
}

@Composable
private fun FriendshipOption(checked: Boolean, label: Int, onChecked: (Boolean) -> Unit) {
    Row(
        modifier = Modifier.toggleable(value = checked, role = Role.Checkbox, onValueChange = onChecked),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Checkbox(checked = checked, onCheckedChange = null)
        Text(stringResource(label))
    }
}

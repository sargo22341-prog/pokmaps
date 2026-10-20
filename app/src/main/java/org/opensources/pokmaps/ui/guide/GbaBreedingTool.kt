package org.opensources.pokmaps.ui.guide

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FilterChip
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.BreedingItem
import org.opensources.pokmaps.domain.guide.BreedingIv
import org.opensources.pokmaps.domain.guide.ParentSex
import org.opensources.pokmaps.domain.guide.ParentValues

@Composable
internal fun GbaParentValues(
    sexes: List<ParentSex>,
    values: ParentValues,
    first: Boolean,
    sinnoh: Boolean = false,
    onAction: (BreedingAction) -> Unit
) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        sexes.forEach { sex ->
            FilterChip(
                selected = values.sex == sex,
                label = { Text(stringResource(sex.label())) },
                onClick = { onAction(BreedingAction.Values(first, values.copy(sex = sex))) }
            )
        }
    }
    GbaParentItem(values.item, sinnoh) { onAction(BreedingAction.Values(first, values.copy(item = it))) }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        BreedingIv.entries.chunked(2).forEach { stats ->
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                stats.forEach { stat ->
                    OutlinedTextField(
                        value = values.ivs[stat.ordinal]?.toString().orEmpty(),
                        modifier = Modifier.weight(1f),
                        singleLine = true,
                        label = { Text(stringResource(R.string.breeding_iv, stringResource(stat.label()))) },
                        onValueChange = { text ->
                            val iv = text.toIntOrNull()?.takeIf { it in 0..31 }
                            if (text.isEmpty() || iv != null) {
                                val ivs = values.ivs.mapIndexed { index, old -> if (index == stat.ordinal) iv else old }
                                onAction(BreedingAction.Values(first, values.copy(ivs = ivs)))
                            }
                        }
                    )
                }
            }
        }
    }
}

@Composable
private fun GbaParentItem(item: BreedingItem, sinnoh: Boolean, onItem: (BreedingItem) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Column {
        OutlinedButton(onClick = { expanded = true }) {
            Text(stringResource(R.string.breeding_held_item, stringResource(item.label())))
        }
        DropdownMenu(expanded, onDismissRequest = { expanded = false }) {
            BreedingItem.entries.filter { sinnoh || !it.sinnohOnly }.forEach { choice ->
                DropdownMenuItem(text = { Text(stringResource(choice.label())) }, onClick = {
                    expanded = false
                    onItem(choice)
                })
            }
        }
    }
}

@Composable
internal fun GbaBreedingResult(state: BreedingUiState) {
    Text(stringResource(if (state.sinnoh) R.string.breeding_sinnoh_ivs else R.string.breeding_gba_ivs))
    BreedingIv.entries.forEach { stat ->
        val unknown = stringResource(R.string.breeding_unknown_iv)
        Text(
            stringResource(
                R.string.breeding_iv_values,
                stringResource(stat.label()),
                state.first.ivs[stat.ordinal]?.toString() ?: unknown,
                state.second.ivs[stat.ordinal]?.toString() ?: unknown
            )
        )
    }
    Text(stringResource(if (state.sinnoh) R.string.breeding_sinnoh_abilities else R.string.breeding_gba_abilities))
    state.babyAbilities.forEach { (name, abilities) ->
        Text(
            stringResource(
                R.string.breeding_child_abilities,
                name,
                abilities
            )
        )
    }
    val natureParent = state.natureParent
    Text(
        if (natureParent == null) {
            stringResource(R.string.breeding_random_nature)
        } else {
            stringResource(
                if (state.sinnoh) R.string.breeding_sinnoh_everstone else R.string.breeding_everstone_nature,
                natureParent + 1
            )
        }
    )
}

private fun BreedingItem.label(): Int = when (this) {
    BreedingItem.NONE -> R.string.catch_status_none
    BreedingItem.SEA_INCENSE -> R.string.breeding_sea_incense
    BreedingItem.LAX_INCENSE -> R.string.breeding_lax_incense
    BreedingItem.LIGHT_BALL -> R.string.breeding_light_ball
    BreedingItem.EVERSTONE -> R.string.breeding_everstone
    BreedingItem.ODD_INCENSE -> R.string.breeding_odd_incense
    BreedingItem.ROCK_INCENSE -> R.string.breeding_rock_incense
    BreedingItem.FULL_INCENSE -> R.string.breeding_full_incense
    BreedingItem.WAVE_INCENSE -> R.string.breeding_wave_incense
    BreedingItem.ROSE_INCENSE -> R.string.breeding_rose_incense
    BreedingItem.LUCK_INCENSE -> R.string.breeding_luck_incense
    BreedingItem.PURE_INCENSE -> R.string.breeding_pure_incense
}

private fun BreedingIv.label(): Int = when (this) {
    BreedingIv.HP -> R.string.breeding_iv_hp
    BreedingIv.ATTACK -> R.string.breeding_iv_attack
    BreedingIv.DEFENSE -> R.string.breeding_iv_defense
    BreedingIv.SPEED -> R.string.breeding_iv_speed
    BreedingIv.SPECIAL_ATTACK -> R.string.breeding_iv_special_attack
    BreedingIv.SPECIAL_DEFENSE -> R.string.breeding_iv_special_defense
}

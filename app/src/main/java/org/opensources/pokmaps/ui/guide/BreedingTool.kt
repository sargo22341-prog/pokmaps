package org.opensources.pokmaps.ui.guide

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Checkbox
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.BreedingStatus
import org.opensources.pokmaps.domain.guide.GuideTarget
import org.opensources.pokmaps.domain.guide.ParentSex
import org.opensources.pokmaps.domain.guide.ParentValues
import org.opensources.pokmaps.domain.pokemon.LearnedMove
import org.opensources.pokmaps.ui.common.SheetPlaceholder

@Composable
internal fun BreedingRoute(onPreview: (GuideTarget) -> Unit, viewModel: BreedingViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    BreedingTool(state, viewModel::onAction, onPreview)
}

@Composable
internal fun BreedingTool(
    state: BreedingUiState,
    onAction: (BreedingAction) -> Unit,
    onPreview: (GuideTarget) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(stringResource(R.string.breeding_tool), style = MaterialTheme.typography.titleLarge)
        if (!state.firstSelected && !state.loading && !state.failed && state.catalog?.pokemon?.isNotEmpty() == true) {
            BreedingSpeciesSelector(0, stringResource(R.string.breeding_choose), state, true, onAction, onPreview)
        } else if (state.loading || state.failed || state.pair == null) {
            SheetPlaceholder(state.loading, stringResource(R.string.guide_empty), failed = state.failed)
            if (state.failed) {
                TextButton(onClick = {
                    onAction(BreedingAction.Retry)
                }) { Text(stringResource(R.string.guide_retry)) }
            }
        } else {
            BreedingParent(state, true, onAction, onPreview)
            if (state.partners.isNotEmpty()) BreedingParent(state, false, onAction, onPreview)
            state.status?.let {
                Text(
                    stringResource(it.label()),
                    style = MaterialTheme.typography.titleMedium,
                    color = if (state.possible) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.error
                )
            }
            if (state.possible) {
                Text(stringResource(R.string.breeding_offspring), style = MaterialTheme.typography.titleSmall)
                state.pair.babies.forEach { child ->
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(child.name, modifier = Modifier.weight(1f))
                        BreedingPokemonSprite(child.id, child.name, onPreview)
                    }
                    state.offspringMoves.firstOrNull {
                        it.first == child.id
                    }?.second.orEmpty().forEach { Text(it.name) }
                }
                Text(stringResource(R.string.breeding_inheritance_note), style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
private fun BreedingParent(
    state: BreedingUiState,
    first: Boolean,
    onAction: (BreedingAction) -> Unit,
    onPreview: (GuideTarget) -> Unit
) {
    val pair = state.pair ?: return
    val parent = if (first) pair.first else pair.second
    val values = if (first) state.first else state.second
    val sexes = if (first) state.firstSexes else state.secondSexes
    val moves = if (first) state.firstMoves else state.secondMoves
    var selectingMoves by remember { mutableStateOf(false) }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(stringResource(if (first) R.string.breeding_parent_one else R.string.breeding_parent_two))
        BreedingSpeciesSelector(parent.id, parent.name, state, first, onAction, onPreview)
        BreedingParentValues(sexes, values, first, onAction)
        TextButton(onClick = { selectingMoves = true }) {
            Text(stringResource(R.string.breeding_known_moves, values.moves.size))
        }
    }
    if (selectingMoves) {
        ParentMovesDialog(moves, values, { selectingMoves = false }) {
            onAction(BreedingAction.Values(first, it))
        }
    }
}

@Composable
private fun BreedingParentValues(
    sexes: List<ParentSex>,
    values: ParentValues,
    first: Boolean,
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
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        BreedingDv(values.defense, R.string.breeding_defense, Modifier.weight(1f)) {
            onAction(BreedingAction.Values(first, values.copy(defense = it)))
        }
        BreedingDv(values.special, R.string.breeding_special, Modifier.weight(1f)) {
            onAction(BreedingAction.Values(first, values.copy(special = it)))
        }
    }
}

@Composable
private fun BreedingDv(value: Int?, label: Int, modifier: Modifier, onValue: (Int?) -> Unit) {
    OutlinedTextField(
        value = value?.toString().orEmpty(),
        singleLine = true,
        modifier = modifier,
        label = { Text(stringResource(label)) },
        onValueChange = { text ->
            if (text.isEmpty()) {
                onValue(null)
            } else {
                text.toIntOrNull()?.takeIf { it in 0..15 }?.let(onValue)
            }
        }
    )
}

@Composable
private fun ParentMovesDialog(
    moves: List<LearnedMove>,
    values: ParentValues,
    onClose: () -> Unit,
    onValues: (ParentValues) -> Unit
) {
    AlertDialog(
        onDismissRequest = onClose,
        title = { Text(stringResource(R.string.breeding_move_order)) },
        text = {
            LazyColumn(Modifier.heightIn(max = 360.dp)) {
                items(moves, key = { it.moveId }) { move ->
                    val selected = move.moveId in values.moves
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(
                            checked = selected,
                            enabled = selected || values.moves.size < 4,
                            onCheckedChange = { checked ->
                                onValues(
                                    values.copy(
                                        moves =
                                            if (checked) values.moves + move.moveId else values.moves - move.moveId
                                    )
                                )
                            }
                        )
                        Text(move.name)
                    }
                }
            }
        },
        confirmButton = { TextButton(onClick = onClose) { Text(stringResource(R.string.guide_close)) } }
    )
}

private fun ParentSex.label(): Int = when (this) {
    ParentSex.MALE -> R.string.breeding_male
    ParentSex.FEMALE -> R.string.breeding_female
    ParentSex.GENDERLESS -> R.string.breeding_genderless
}

private fun BreedingStatus.label(): Int = when (this) {
    BreedingStatus.NO_EGGS -> R.string.breeding_no_eggs
    BreedingStatus.DIFFERENT_GROUPS -> R.string.breeding_different_groups
    BreedingStatus.SAME_SEX -> R.string.breeding_same_sex
    BreedingStatus.RELATED_DVS -> R.string.breeding_related
    BreedingStatus.POSSIBLE -> R.string.breeding_possible
    BreedingStatus.COMPATIBLE -> R.string.breeding_compatible
}

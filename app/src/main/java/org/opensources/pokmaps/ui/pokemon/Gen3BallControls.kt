package org.opensources.pokmaps.ui.pokemon

import androidx.compose.material3.FilterChip
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.res.stringResource
import org.opensources.pokmaps.R

@Composable
internal fun Gen3BallControls(catch: CatchUiState, onAction: (PokemonAction) -> Unit) {
    FilterChip(
        selected = catch.underwater,
        onClick = { onAction(PokemonAction.ToggleUnderwater) },
        label = { Text(stringResource(R.string.catch_underwater)) }
    )
    FilterChip(
        selected = catch.alreadyCaught,
        onClick = { onAction(PokemonAction.ToggleAlreadyCaught) },
        label = { Text(stringResource(R.string.catch_already_caught)) }
    )
    Text(stringResource(R.string.catch_elapsed_turns, catch.elapsedTurns))
    Slider(
        value = catch.elapsedTurns.toFloat(),
        onValueChange = { onAction(PokemonAction.SetElapsedTurns(it.toInt())) },
        valueRange = 0f..30f,
        steps = 29
    )
}

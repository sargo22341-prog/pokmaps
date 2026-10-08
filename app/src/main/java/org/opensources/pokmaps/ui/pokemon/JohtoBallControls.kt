package org.opensources.pokmaps.ui.pokemon

import androidx.compose.material3.FilterChip
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.res.stringResource
import org.opensources.pokmaps.R

@Composable
internal fun JohtoBallControls(catch: CatchUiState, onAction: (PokemonAction) -> Unit) {
    Text(stringResource(R.string.catch_player_level, catch.playerLevel))
    Slider(
        value = catch.playerLevel.toFloat(),
        onValueChange = { onAction(PokemonAction.SetPlayerLevel(it.toInt())) },
        valueRange = 1f..PokemonViewModel.MAX_LEVEL.toFloat()
    )
    FilterChip(
        selected = catch.fishing,
        onClick = { onAction(PokemonAction.ToggleFishing) },
        label = { Text(stringResource(R.string.catch_fishing)) }
    )
    FilterChip(
        selected = catch.sameSpeciesAndGender,
        onClick = { onAction(PokemonAction.ToggleLoveBonus) },
        label = { Text(stringResource(R.string.catch_love_bonus)) }
    )
}

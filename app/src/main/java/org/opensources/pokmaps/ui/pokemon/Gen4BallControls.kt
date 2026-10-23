package org.opensources.pokmaps.ui.pokemon

import androidx.compose.material3.FilterChip
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.res.stringResource
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.pokemon.CaptureEnvironment

@Composable
internal fun Gen4BallControls(catch: CatchUiState, onAction: (PokemonAction) -> Unit) {
    val environments = if (catch.hgss) {
        listOf(
            CaptureEnvironment.NORMAL,
            CaptureEnvironment.HGSS_SAFARI,
            CaptureEnvironment.BUG_CONTEST,
            CaptureEnvironment.PAL_PARK
        )
    } else {
        listOf(CaptureEnvironment.NORMAL, CaptureEnvironment.GREAT_MARSH, CaptureEnvironment.PAL_PARK)
    }
    environments.forEach { environment ->
        FilterChip(
            selected = catch.environment == environment,
            onClick = { onAction(PokemonAction.SetCaptureEnvironment(environment)) },
            label = { Text(stringResource(environment.label)) }
        )
    }
    when (catch.environment) {
        CaptureEnvironment.NORMAL -> {
            NormalBallControls(catch, onAction)
            if (catch.hgss) JohtoBallControls(catch, onAction)
        }

        CaptureEnvironment.GREAT_MARSH, CaptureEnvironment.HGSS_SAFARI -> {
            Text(stringResource(R.string.catch_safari_stage, catch.safariStage))
            Slider(
                value = catch.safariStage.toFloat(),
                onValueChange = { onAction(PokemonAction.SetSafariStage(it.toInt())) },
                valueRange = 0f..12f,
                steps = 11
            )
        }

        CaptureEnvironment.BUG_CONTEST -> Unit

        CaptureEnvironment.PAL_PARK -> Text(stringResource(R.string.catch_pal_park_note))
    }
}

@Composable
private fun NormalBallControls(catch: CatchUiState, onAction: (PokemonAction) -> Unit) {
    FilterChip(
        selected = catch.nightOrCave,
        onClick = { onAction(PokemonAction.ToggleNightOrCave) },
        label = { Text(stringResource(R.string.catch_night_or_cave)) }
    )
    FilterChip(
        selected = catch.waterTerrain,
        onClick = { onAction(PokemonAction.ToggleWaterTerrain) },
        label = { Text(stringResource(R.string.catch_water_terrain)) }
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

private val CaptureEnvironment.label: Int
    get() = when (this) {
        CaptureEnvironment.HGSS_SAFARI -> R.string.catch_hgss_safari
        CaptureEnvironment.BUG_CONTEST -> R.string.catch_bug_contest
        CaptureEnvironment.NORMAL -> R.string.catch_normal_battle
        CaptureEnvironment.GREAT_MARSH -> R.string.catch_great_marsh
        CaptureEnvironment.PAL_PARK -> R.string.catch_pal_park
    }

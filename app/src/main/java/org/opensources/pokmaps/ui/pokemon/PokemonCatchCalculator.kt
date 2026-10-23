package org.opensources.pokmaps.ui.pokemon

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.domain.pokemon.Ball
import org.opensources.pokmaps.domain.pokemon.CaptureEnvironment
import org.opensources.pokmaps.domain.pokemon.CaptureGeneration
import org.opensources.pokmaps.domain.pokemon.CatchStatus
import org.opensources.pokmaps.ui.common.PixelArt
import org.opensources.pokmaps.ui.common.PixelArtImage
import org.opensources.pokmaps.ui.common.formatNumber

@Composable
internal fun CatchCalculator(catch: CatchUiState, onAction: (PokemonAction) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(stringResource(R.string.catch_level, catch.level), style = MaterialTheme.typography.bodyMedium)
        Slider(
            value = catch.level.toFloat(),
            onValueChange = { onAction(PokemonAction.SetCatchLevel(it.toInt())) },
            valueRange = 1f..PokemonViewModel.MAX_LEVEL.toFloat()
        )
        when (catch.generation) {
            CaptureGeneration.GEN1 -> Unit
            CaptureGeneration.GEN2 -> JohtoBallControls(catch, onAction)
            CaptureGeneration.GEN4 -> Gen4BallControls(catch, onAction)
            CaptureGeneration.GEN3 -> Gen3BallControls(catch, onAction)
        }
        if (catch.generation != CaptureGeneration.GEN4 ||
            catch.environment in listOf(CaptureEnvironment.NORMAL, CaptureEnvironment.BUG_CONTEST)
        ) {
            HealthControls(catch, onAction)
        }
        BallProbabilities(catch)
        if (catch.blockedBalls.isNotEmpty()) {
            Text(stringResource(R.string.catch_engine_blocked), color = MaterialTheme.colorScheme.error)
        }
        CatchNote(catch.generation)
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun HealthControls(catch: CatchUiState, onAction: (PokemonAction) -> Unit) {
    Text(stringResource(R.string.catch_hp), style = MaterialTheme.typography.bodyMedium)
    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        HpChoice.entries.forEach { hp ->
            FilterChip(selected = catch.hp == hp, onClick = {
                onAction(PokemonAction.SetCatchHp(hp))
            }, label = { Text(stringResource(hp.label)) })
        }
    }
    Text(stringResource(R.string.status_label), style = MaterialTheme.typography.bodyMedium)
    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        CatchStatus.entries.forEach { status ->
            FilterChip(
                selected = catch.status == status,
                onClick = { onAction(PokemonAction.SetCatchStatus(status)) },
                label = { Text(stringResource(status.label)) }
            )
        }
    }
}

@Composable
private fun CatchNote(generation: CaptureGeneration) {
    Text(
        stringResource(
            when (generation) {
                CaptureGeneration.GEN1 -> R.string.catch_note
                CaptureGeneration.GEN2 -> R.string.catch_note_gen2
                CaptureGeneration.GEN4 -> R.string.catch_note_gen4
                CaptureGeneration.GEN3 -> R.string.catch_note_gen3
            }
        ),
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant
    )
}

@Composable
private fun BallProbabilities(catch: CatchUiState) {
    Column {
        catch.probabilities.forEach { (ball, probability) ->
            val best = ball == catch.best
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                PixelArtImage(Sprites.item(ball.itemIdentifier), PixelArt.ITEM_ICON, 64.dp, contentDescription = null)
                Column(Modifier.weight(1f)) {
                    Text(stringResource(ball.label), fontWeight = if (best) FontWeight.Bold else FontWeight.Normal)
                    if (best) {
                        Text(
                            stringResource(R.string.catch_best),
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }
                }
                Text(
                    stringResource(R.string.encounter_chance, formatNumber(probability * PERCENT)),
                    fontWeight = if (best) FontWeight.Bold else FontWeight.Normal
                )
            }
        }
    }
}

private val HpChoice.label: Int
    get() = when (this) {
        HpChoice.FULL -> R.string.catch_hp_full
        HpChoice.HALF -> R.string.catch_hp_half
        HpChoice.QUARTER -> R.string.catch_hp_quarter
        HpChoice.ONE -> R.string.catch_hp_one
    }

private val CatchStatus.label: Int
    get() = when (this) {
        CatchStatus.NONE -> R.string.catch_status_none
        CatchStatus.SLEEP_OR_FREEZE -> R.string.catch_status_sleep
        CatchStatus.PARALYSIS_BURN_OR_POISON -> R.string.catch_status_paralysis
    }

private val Ball.label: Int
    get() = when (this) {
        Ball.POKE -> R.string.ball_poke
        Ball.GREAT -> R.string.ball_great
        Ball.ULTRA -> R.string.ball_ultra
        Ball.SAFARI -> R.string.ball_safari
        Ball.MASTER -> R.string.ball_master
        Ball.LEVEL -> R.string.ball_level
        Ball.LURE -> R.string.ball_lure
        Ball.MOON -> R.string.ball_moon
        Ball.FRIEND -> R.string.ball_friend
        Ball.LOVE -> R.string.ball_love
        Ball.HEAVY -> R.string.ball_heavy
        Ball.FAST -> R.string.ball_fast
        Ball.PARK -> R.string.ball_park
        Ball.NET -> R.string.ball_net
        Ball.DIVE -> R.string.ball_dive
        Ball.NEST -> R.string.ball_nest
        Ball.REPEAT -> R.string.ball_repeat
        Ball.TIMER -> R.string.ball_timer
        Ball.LUXURY -> R.string.ball_luxury
        Ball.DUSK -> R.string.ball_dusk
        Ball.HEAL -> R.string.ball_heal
        Ball.QUICK -> R.string.ball_quick
        Ball.SPORT -> R.string.ball_sport
        Ball.CHERISH -> R.string.ball_cherish
        Ball.PREMIER -> R.string.ball_premier
    }

private const val PERCENT = 100

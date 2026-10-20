package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.ColorMatrix
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.map.TrainerTeam
import org.opensources.pokmaps.domain.model.Sprites

@Composable
internal fun TrainerBattleSelector(teams: List<TrainerTeam>, selected: Int?, onSelect: (Int?) -> Unit) {
    val battles = teams.map { it.rematch }.distinct().sortedBy { it ?: 0 }
    if (battles.size > 1) {
        CompactSelect(selected, battles, onSelect) { battle ->
            when {
                battle == null -> stringResource(R.string.trainer_first_battle)
                teams.any { it.variant != null } -> stringResource(R.string.trainer_battle_number, battle + 1)
                else -> stringResource(R.string.map_trainer_rematch, battle)
            }
        }
    }
}

@Composable
fun TrainerPartyBalls(team: TrainerTeam) {
    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        repeat(6) { slot ->
            val filled = slot < team.members.size
            PixelArtImage(
                Sprites.item("poke-ball"),
                PixelArt.ITEM_ICON,
                16.dp,
                stringResource(if (filled) R.string.trainer_party_ball else R.string.trainer_party_empty),
                alpha = if (filled) 1f else 0.35f,
                colorFilter = if (filled) {
                    null
                } else {
                    ColorFilter.colorMatrix(
                        ColorMatrix().apply {
                            setToSaturation(0f)
                        }
                    )
                }
            )
        }
    }
}

package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.runtime.Composable
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
            battle?.let { stringResource(R.string.map_trainer_rematch, it) }
                ?: stringResource(R.string.trainer_first_battle)
        }
    }
}

@Composable
internal fun TrainerPartyBalls(team: TrainerTeam) {
    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        team.members.forEach { _ ->
            PixelArtImage(
                Sprites.item("poke-ball"),
                PixelArt.ITEM_ICON,
                16.dp,
                stringResource(R.string.trainer_party_ball)
            )
        }
    }
}

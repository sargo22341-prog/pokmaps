package org.opensources.pokmaps.ui.move

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.hoenn.ContestCategory
import org.opensources.pokmaps.domain.hoenn.ContestMove

@Composable
internal fun ContestSection(contest: ContestMove) {
    val category = when (contest.category) {
        ContestCategory.COOL -> R.string.contest_cool
        ContestCategory.BEAUTY -> R.string.contest_beauty
        ContestCategory.CUTE -> R.string.contest_cute
        ContestCategory.SMART -> R.string.contest_smart
        ContestCategory.TOUGH -> R.string.contest_tough
    }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(stringResource(category))
        Text(stringResource(R.string.contest_hearts, contest.appeal, contest.jam))
        Text(contest.effect)
        if (contest.previous.isNotEmpty()) {
            Text(stringResource(R.string.contest_previous, contest.previous.joinToString(", ")))
        }
    }
}

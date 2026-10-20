package org.opensources.pokmaps.ui.map

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.FilledTonalIconToggleButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import org.opensources.pokmaps.domain.model.EncounterPeriods
import org.opensources.pokmaps.domain.model.TimeFilter

@Composable
internal fun EncounterPeriodButtons(periods: EncounterPeriods, onToggle: (TimeFilter) -> Unit) {
    Row {
        PeriodButton(TimeFilter.ALL, periods.allSelected, onToggle)
        periods.available.forEach { period ->
            PeriodButton(period, period.time in periods.selected, onToggle)
        }
    }
}

@Composable
private fun PeriodButton(period: TimeFilter, selected: Boolean, onToggle: (TimeFilter) -> Unit) {
    FilledTonalIconToggleButton(checked = selected, onCheckedChange = { onToggle(period) }) {
        Box(Modifier.alpha(if (selected) 1f else 0.35f)) { TimeIcon(period) }
    }
}

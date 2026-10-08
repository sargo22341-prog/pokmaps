package org.opensources.pokmaps.ui.map

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import org.opensources.pokmaps.domain.model.TimeFilter

/** Le voile évolue progressivement sans intercepter les gestes de la carte. */
@Composable
internal fun MapDaylight(time: TimeFilter) {
    val color by animateColorAsState(
        targetValue = when (time) {
            TimeFilter.MORNING -> Color(0x24FFB45E)
            TimeFilter.DAY -> Color(0x08FFF3B0)
            TimeFilter.NIGHT -> Color(0x80302565)
            TimeFilter.ALL -> Color.Transparent
        },
        animationSpec = tween(1400),
        label = "daylight"
    )
    Canvas(Modifier.fillMaxSize()) { drawRect(color) }
}

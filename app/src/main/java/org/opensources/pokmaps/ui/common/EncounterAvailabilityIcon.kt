package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.ColorMatrix
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R

@Composable
internal fun EncounterAvailabilityIcon(image: Int, label: String, available: Boolean, size: Dp = 28.dp) {
    Image(
        painterResource(image),
        contentDescription = if (available) label else "$label : ${stringResource(R.string.water_unavailable)}",
        modifier = Modifier.size(size).alpha(if (available) 1f else 0.3f),
        colorFilter = if (available) null else ColorFilter.colorMatrix(ColorMatrix().apply { setToSaturation(0f) })
    )
}

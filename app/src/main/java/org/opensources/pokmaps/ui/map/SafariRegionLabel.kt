package org.opensources.pokmaps.ui.map

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.MapRegion
import ovh.plrapps.mapcompose.api.scale
import ovh.plrapps.mapcompose.ui.state.MapState

/** Réduit les étiquettes en vue d'ensemble, puis plafonne leur taille quand on rapproche le terrain. */
@Composable
internal fun SafariRegionLabel(mapState: MapState, region: MapRegion) {
    val density = LocalDensity.current.density
    val size by remember(mapState, region.width, density) {
        derivedStateOf { (region.width * mapState.scale / density / 88).toFloat().coerceIn(0.25f, 1f) }
    }
    Text(
        stringResource(checkNotNull(SAFARI_LABELS[region.identifier])),
        color = MaterialTheme.colorScheme.onSurface,
        fontSize = 10.sp * size,
        lineHeight = 12.sp * size,
        fontWeight = FontWeight.Bold,
        maxLines = 1,
        modifier = Modifier
            .background(MaterialTheme.colorScheme.surface.copy(alpha = 0.9f), RoundedCornerShape(3.dp))
            .padding(horizontal = 4.dp * size, vertical = 2.dp * size)
    )
}

private val SAFARI_LABELS = mapOf(
    "safari-zone-01" to R.string.map_safari_plains,
    "safari-zone-02" to R.string.map_safari_meadow,
    "safari-zone-03" to R.string.map_safari_savannah,
    "safari-zone-04" to R.string.map_safari_peak,
    "safari-zone-05" to R.string.map_safari_rocky_beach,
    "safari-zone-06" to R.string.map_safari_wetland,
    "safari-zone-07" to R.string.map_safari_forest,
    "safari-zone-08" to R.string.map_safari_swamp,
    "safari-zone-09" to R.string.map_safari_marsh,
    "safari-zone-10" to R.string.map_safari_wasteland,
    "safari-zone-11" to R.string.map_safari_mountain,
    "safari-zone-12" to R.string.map_safari_desert,
    "safari-zone-entrance-exterior" to R.string.map_safari_entrance
)

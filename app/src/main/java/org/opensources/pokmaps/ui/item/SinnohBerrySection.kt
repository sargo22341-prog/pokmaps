package org.opensources.pokmaps.ui.item

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.sinnoh.Mulch
import org.opensources.pokmaps.domain.sinnoh.SinnohBerry
import org.opensources.pokmaps.ui.common.SheetSection

@Composable
internal fun SinnohBerrySection(berry: SinnohBerry?) {
    if (berry == null) return
    SheetSection(stringResource(R.string.berry_growing)) {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(stringResource(R.string.berry_growth, berry.stageHours, berry.stageHours * 4, 2, berry.maxYield))
            Text(stringResource(R.string.sinnoh_berry_water, berry.drainRate))
            Text(stringResource(R.string.berry_flavors, *berry.flavors.toTypedArray()))
            Text(stringResource(R.string.berry_smoothness, berry.smoothness))
            Text(stringResource(R.string.sinnoh_poffin_flavors))
            Text(
                stringResource(
                    R.string.sinnoh_mulch_growth,
                    berry.stageMinutes(Mulch.GROWTH),
                    berry.hourlyDrain(Mulch.GROWTH)
                )
            )
            Text(
                stringResource(
                    R.string.sinnoh_mulch_damp,
                    berry.stageMinutes(Mulch.DAMP),
                    berry.hourlyDrain(Mulch.DAMP)
                )
            )
            Text(stringResource(R.string.sinnoh_mulch_stable))
            Text(stringResource(R.string.sinnoh_mulch_gooey))
        }
    }
}

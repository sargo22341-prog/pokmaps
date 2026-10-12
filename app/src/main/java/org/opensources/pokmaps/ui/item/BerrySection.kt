package org.opensources.pokmaps.ui.item

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.hoenn.Berry
import org.opensources.pokmaps.ui.common.SheetSection

@Composable
internal fun BerrySection(berry: Berry?) {
    if (berry == null) return
    SheetSection(stringResource(R.string.berry_growing)) {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(
                stringResource(
                    R.string.berry_growth,
                    berry.stageHours,
                    berry.stageHours * 4,
                    berry.minYield,
                    berry.maxYield
                )
            )
            Text(
                stringResource(
                    R.string.berry_flavors,
                    berry.flavors[0],
                    berry.flavors[1],
                    berry.flavors[2],
                    berry.flavors[3],
                    berry.flavors[4]
                )
            )
            Text(stringResource(R.string.berry_smoothness, berry.smoothness))
            Text(
                stringResource(
                    if (berry.identifier ==
                        "enigma-berry"
                    ) {
                        R.string.berry_enigma
                    } else {
                        R.string.berry_water
                    }
                )
            )
        }
    }
}

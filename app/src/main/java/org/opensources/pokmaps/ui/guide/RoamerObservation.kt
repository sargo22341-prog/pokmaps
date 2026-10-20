package org.opensources.pokmaps.ui.guide

import androidx.compose.foundation.layout.Column
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.res.stringResource
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.SinnohRoamerObservations

@Composable
internal fun RoamerObservation(place: String?, onObserve: (String?) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Column {
        OutlinedButton(onClick = { expanded = true }) {
            Text(stringResource(R.string.roamer_observation, routeLabel(place)))
        }
        DropdownMenu(expanded, onDismissRequest = { expanded = false }) {
            (listOf(null) + SinnohRoamerObservations.places).forEach { route ->
                DropdownMenuItem(text = { Text(routeLabel(route)) }, onClick = {
                    expanded = false
                    onObserve(route)
                })
            }
        }
    }
}

@Composable
private fun routeLabel(place: String?): String = when (place) {
    null -> stringResource(R.string.roamer_not_observed)

    "valley-windworks" -> stringResource(R.string.roamer_windworks)

    "fuego-ironworks" -> stringResource(R.string.roamer_ironworks)

    else -> {
        val parts = place.split("-")
        val suffix = when (parts.getOrNull(2)) {
            null -> R.string.roamer_route
            "south" -> R.string.roamer_route_south
            "north" -> R.string.roamer_route_north
            "west" -> R.string.roamer_route_west
            "east" -> R.string.roamer_route_east
            else -> error("Route inconnue : $place")
        }
        stringResource(suffix, parts[1].toInt())
    }
}

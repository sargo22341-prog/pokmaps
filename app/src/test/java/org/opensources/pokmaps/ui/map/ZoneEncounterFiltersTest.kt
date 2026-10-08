package org.opensources.pokmaps.ui.map

import android.content.Context
import androidx.compose.foundation.layout.Column
import androidx.compose.ui.test.hasClickAction
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.performClick
import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.EncounterTime
import org.opensources.pokmaps.domain.model.TimeFilter
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class ZoneEncounterFiltersTest {
    @get:Rule
    val compose = createComposeRule()

    private val context: Context = ApplicationProvider.getApplicationContext()

    private fun encounter(name: String, method: String, time: EncounterTime) = Encounter(
        4, "Or", 1, "Route", 16, name, method, method, 1, false,
        2, 4, 30.0, 1, null, null, setOf(time)
    )

    @Test
    fun listStartsWithMapTimeAndChangesOnlyItsOwnFilter() {
        val map = MapUiState(time = TimeFilter.MORNING)
        val encounters = listOf(
            encounter("Roucool", "walk", EncounterTime.MORNING),
            encounter("Hoothoot", "walk", EncounterTime.NIGHT)
        )
        val zone = MapZone(1, "Route", emptyList(), loading = false, allEncounters = encounters)
        compose.setContent { Column { TimedZoneEncounters(zone, emptySet(), map.time) {} } }
        compose.onNode(hasText("Roucool")).assertExists()
        compose.onNode(hasText("Hoothoot")).assertDoesNotExist()
        click(R.string.time_morning)
        compose.onNode(hasText("Roucool")).assertDoesNotExist()
        click(R.string.time_day)
        compose.onNode(hasText("Hoothoot")).assertExists()
        assertEquals(TimeFilter.MORNING, map.time)
    }

    @Test
    fun captureFilterCanReturnToAllWithoutChangingZone() {
        val encounters = listOf(
            encounter("Roucool", "walk", EncounterTime.DAY),
            encounter("Magicarpe", "old-rod", EncounterTime.DAY),
            encounter("Tentacool", "surf", EncounterTime.DAY)
        )
        val zone = MapZone(1, "Route", emptyList(), loading = false, encounters = encounters)
        compose.setContent { Column { FilteredZoneEncounters(zone, emptySet()) {} } }
        click(R.string.map_method_walk)
        compose.onNode(hasText("Roucool")).assertExists()
        compose.onNode(hasText("Magicarpe")).assertDoesNotExist()
        click(R.string.method_fishing)
        compose.onNode(hasText("Magicarpe")).assertExists()
        compose.onNode(hasText("Tentacool")).assertDoesNotExist()
        click(R.string.method_surf)
        compose.onNode(hasText("Tentacool")).assertExists()
        click(R.string.time_all)
        compose.onNode(hasText("Roucool")).assertExists()
        compose.onNode(hasText("Magicarpe")).assertExists()
        assertEquals(encounters, zone.encounters)
    }

    private fun click(label: Int) {
        compose.onNode(hasText(context.getString(label)) and hasClickAction()).performClick()
    }
}

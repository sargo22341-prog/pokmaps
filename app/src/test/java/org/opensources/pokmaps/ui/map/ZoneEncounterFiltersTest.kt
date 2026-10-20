package org.opensources.pokmaps.ui.map

import android.content.Context
import androidx.compose.foundation.layout.Column
import androidx.compose.ui.test.hasClickAction
import androidx.compose.ui.test.hasContentDescription
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

    private val pokemonIds = mapOf(
        "Roucool" to 16,
        "Hoothoot" to 163,
        "Coquiperl" to 366,
        "Barpau" to 349,
        "Tentacool" to 72,
        "Kecleon" to 352,
        "Magicarpe" to 129,
        "\u00c9voli" to 133
    )

    private fun encounter(name: String, method: String, time: EncounterTime) = Encounter(
        4, "Or", 1, "Route", pokemonIds.getValue(name), name, method, method, 1, false,
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
        assertNoTimeButton(R.string.time_day)
        selectTime(R.string.time_morning, R.string.time_night)
        compose.onNode(hasText("Roucool")).assertDoesNotExist()
        compose.onNode(hasText("Hoothoot")).assertExists()
        assertEquals(TimeFilter.MORNING, map.time)
    }

    @Test
    fun divingAndFeebasFishingHaveSeparateFilters() {
        val encounters = listOf(
            encounter("Coquiperl", "seaweed", EncounterTime.DAY),
            encounter("Barpau", "feebas-tile-fishing", EncounterTime.DAY),
            encounter("Tentacool", "surf", EncounterTime.DAY),
            encounter("Kecleon", "devon-scope", EncounterTime.DAY)
        )
        val zone = MapZone(1, "Route", emptyList(), loading = false, encounters = encounters)
        compose.setContent { Column { FilteredZoneEncounters(zone, emptySet()) {} } }
        click(R.string.method_dive)
        compose.onNode(hasText("Coquiperl")).assertExists()
        compose.onNode(hasText("Barpau")).assertDoesNotExist()
        compose.onNode(hasText("Tentacool")).assertDoesNotExist()
        click(R.string.method_fishing)
        compose.onNode(hasText("Barpau")).assertExists()
        compose.onNode(hasText("Coquiperl")).assertDoesNotExist()
        click(R.string.time_all)
        compose.onNode(hasText("Kecleon")).assertExists()
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

    private fun selectTime(current: Int, target: Int) {
        toggleTime(current)
        toggleTime(target)
    }

    private fun toggleTime(label: Int) {
        compose.onNode(hasContentDescription(context.getString(label)) and hasClickAction()).performClick()
    }

    private fun assertNoTimeButton(label: Int) {
        compose.onNode(hasContentDescription(context.getString(label)) and hasClickAction()).assertDoesNotExist()
    }

    @Test
    fun walkingZoneHidesFishingAndSurf() {
        val encounters = listOf(encounter("Roucool", "walk", EncounterTime.DAY))
        val zone = MapZone(1, "Route", emptyList(), loading = false, encounters = encounters)
        compose.setContent { Column { FilteredZoneEncounters(zone, emptySet()) {} } }
        compose.onNode(hasText(context.getString(R.string.map_method_walk))).assertExists()
        assertNoChip(R.string.method_fishing)
        assertNoChip(R.string.method_surf)
    }

    @Test
    fun emptyZoneHidesAllFilters() {
        val zone = MapZone(1, "Route", emptyList(), loading = false)
        compose.setContent { Column { FilteredZoneEncounters(zone, emptySet()) {} } }
        assertNoCaptureChips()
        compose.onNode(hasText(context.getString(R.string.map_no_encounter))).assertExists()
    }

    @Test
    fun emptyTimedZoneHidesTimeAndCaptureFilters() {
        val zone = MapZone(1, "Route", emptyList(), loading = false)
        compose.setContent { Column { TimedZoneEncounters(zone, emptySet(), TimeFilter.MORNING) {} } }
        assertNoCaptureChips()
        assertNoChip(R.string.time_morning)
        assertNoTimeButton(R.string.time_morning)
        compose.onNode(hasText(context.getString(R.string.time_morning))).assertDoesNotExist()
    }

    @Test
    fun timeChangeHidesUnavailableMethodAndReturnsToAll() {
        val encounters = listOf(
            encounter("Roucool", "walk", EncounterTime.MORNING),
            encounter("Magicarpe", "old-rod", EncounterTime.DAY)
        )
        val zone = MapZone(1, "Route", emptyList(), loading = false, allEncounters = encounters)
        compose.setContent { Column { TimedZoneEncounters(zone, emptySet(), TimeFilter.MORNING) {} } }
        click(R.string.map_method_walk)
        assertNoChip(R.string.method_fishing)
        selectTime(R.string.time_morning, R.string.time_day)
        assertNoChip(R.string.map_method_walk)
        compose.onNode(hasText("Magicarpe")).assertExists()
        click(R.string.method_fishing)
        assertNoTimeButton(R.string.time_night)
        toggleTime(R.string.time_day)
        assertNoCaptureChips()
        toggleTime(R.string.time_all)
        compose.onNode(hasText("Roucool")).assertExists()
        compose.onNode(hasText("Magicarpe")).assertExists()
    }

    @Test
    fun loadingAndFailedZonesHideCaptureFilters() {
        val encounters = listOf(encounter("Roucool", "walk", EncounterTime.DAY))
        val loading = MapZone(1, "Route", emptyList(), encounters = encounters)
        val failed = loading.copy(loading = false, failed = true)
        assertEquals(emptyList<Any>(), loading.availableMethods())
        assertEquals(emptyList<Any>(), failed.availableMethods())
    }

    @Test
    fun giftOnlyZoneKeepsAllAndHidesWildMethods() {
        val encounters = listOf(encounter("Évoli", "gift", EncounterTime.DAY))
        val zone = MapZone(1, "Route", emptyList(), loading = false, encounters = encounters)
        compose.setContent { Column { FilteredZoneEncounters(zone, emptySet()) {} } }
        compose.onNode(hasText("Évoli")).assertExists()
        compose.onNode(hasText(context.getString(R.string.time_all)) and hasClickAction()).assertExists()
        assertNoChip(R.string.map_method_walk)
        assertNoChip(R.string.method_fishing)
        assertNoChip(R.string.method_surf)
    }

    private fun assertNoCaptureChips() {
        assertNoChip(R.string.time_all)
        assertNoChip(R.string.map_method_walk)
        assertNoChip(R.string.method_fishing)
        assertNoChip(R.string.method_surf)
    }

    private fun assertNoChip(label: Int) {
        compose.onNode(hasText(context.getString(label)) and hasClickAction()).assertDoesNotExist()
    }
}

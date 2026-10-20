package org.opensources.pokmaps.ui.map

import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.test.assertIsOff
import androidx.compose.ui.test.assertIsOn
import androidx.compose.ui.test.hasContentDescription
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.performClick
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.EncounterPeriods
import org.opensources.pokmaps.domain.model.EncounterTime
import org.opensources.pokmaps.domain.model.TimeFilter
import org.opensources.pokmaps.domain.model.byTime
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class EncounterPeriodButtonsTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun periodsCanBeDisabledIndependentlyAndAllRestoresThem() {
        val times = mutableStateOf(EncounterTime.entries.toSet())
        val encounters = EncounterTime.entries.map { time ->
            Encounter(
                4, "Or", 1, "Route", 16, "Roucool", "walk", "Marche", 1, false,
                2, 4, 10.0 + time.ordinal, 1, null, null, setOf(time)
            )
        }
        compose.setContent {
            val periods = EncounterPeriods(encounters.byTime(TimeFilter.ALL), times.value)
            EncounterPeriodButtons(periods) { times.value = periods.toggle(it) }
        }
        compose.onNode(hasContentDescription("Matin")).performClick().assertIsOff()
        compose.onNode(hasContentDescription("Jour")).assertIsOn()
        compose.onNode(hasContentDescription("Nuit")).assertIsOn()
        compose.onNode(hasContentDescription("Tout")).assertIsOff().performClick()
        compose.onNode(hasContentDescription("Matin")).assertIsOn()
        compose.onNode(hasContentDescription("Jour")).assertIsOn()
        compose.onNode(hasContentDescription("Nuit")).assertIsOn()
    }
}

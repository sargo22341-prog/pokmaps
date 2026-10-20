package org.opensources.pokmaps.ui.map

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.getUnclippedBoundsInRoot
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithText
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.EncounterTime
import org.opensources.pokmaps.domain.model.TimeFilter
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class EncounterLandscapeOrderTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun allLandPeriodsAndOtherMethodsAreAboveOneWaterZone() {
        val dry = EncounterTime.entries.map { encounter(it, "walk", 16 + it.ordinal, "Terre ${it.name}") }
        val water = EncounterTime.entries.map { encounter(it, "surf", 129 + it.ordinal, "Eau ${it.name}") }
        val gift = encounter(null, "gift", 133, "Cadeau")
        val zone = MapZone(1, "Route", emptyList(), loading = false, encounters = dry + water + gift)
        compose.setContent {
            Column(Modifier.verticalScroll(rememberScrollState())) {
                TimedZoneEncounters(zone, emptySet(), TimeFilter.ALL) {}
            }
        }
        compose.onAllNodesWithText("Zone d’eau").assertCountEquals(1)
        val waterTop = compose.onNodeWithText("Zone d’eau", useUnmergedTree = true)
            .getUnclippedBoundsInRoot().top
        for (name in dry.map { it.pokemonName } + gift.pokemonName) {
            val landBottom = compose.onNodeWithText(name, useUnmergedTree = true)
                .getUnclippedBoundsInRoot().bottom
            assertTrue("$name doit précéder la zone d’eau", landBottom < waterTop)
        }
    }

    private fun encounter(time: EncounterTime?, method: String, pokemonId: Int, name: String) = Encounter(
        4, "Or", 1, "Route", pokemonId, name, method, method, 1, method == "gift",
        5, 10, 30.0, 1, null, null, time?.let { setOf(it) }.orEmpty()
    )
}

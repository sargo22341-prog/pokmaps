package org.opensources.pokmaps.ui.common

import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.groupByMethod
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class WaterEncounterRowsTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun onePokemonShowsFourIconsWithIndependentChancesAndOpensItsProfile() {
        var opened: Int? = null
        val encounters = listOf(encounter("surf", 20.0), encounter("old-rod", 80.0))
        compose.setContent {
            EncounterGroups(
                encounters.groupByMethod(),
                title = { it.pokemonName },
                onClick = { opened = it.pokemonId }
            )
        }
        compose.onAllNodesWithText("Magicarpe").assertCountEquals(1)
        compose.onNodeWithContentDescription("Surf", useUnmergedTree = true).assertExists()
        compose.onNodeWithContentDescription("Canne", useUnmergedTree = true).assertExists()
        compose.onNodeWithContentDescription("Super Canne : Indisponible", useUnmergedTree = true).assertExists()
        compose.onNodeWithContentDescription("Méga Canne : Indisponible", useUnmergedTree = true).assertExists()
        compose.onNodeWithText("20 %", useUnmergedTree = true).assertExists()
        compose.onNodeWithText("80 %", useUnmergedTree = true).assertExists()
        compose.onNodeWithText("Magicarpe").performClick()
        assertEquals(129, opened)
    }

    private fun encounter(method: String, chance: Double) = Encounter(
        1, "Rouge", 1, "Route", 129, "Magicarpe", method, method, 1, false,
        5, 10, chance, 1, null, null
    )
}

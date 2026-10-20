package org.opensources.pokmaps.ui.common

import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
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
        compose.onNodeWithText("Zone d’eau").assertExists()
        val iconBounds = compose.onNodeWithContentDescription("Surf", useUnmergedTree = true)
            .fetchSemanticsNode().boundsInRoot
        val nameBounds = compose.onNodeWithText("Magicarpe", useUnmergedTree = true)
            .fetchSemanticsNode().boundsInRoot
        assertTrue(iconBounds.bottom < nameBounds.top)
        compose.onNodeWithContentDescription("Surf", useUnmergedTree = true).assertExists()
        compose.onNodeWithContentDescription("Canne", useUnmergedTree = true).assertExists()
        compose.onNodeWithContentDescription("Super Canne : Indisponible", useUnmergedTree = true).assertExists()
        compose.onNodeWithContentDescription("Méga Canne : Indisponible", useUnmergedTree = true).assertExists()
        compose.onNodeWithText("20 %", useUnmergedTree = true).assertExists()
        compose.onNodeWithText("80 %", useUnmergedTree = true).assertExists()
        compose.onNodeWithText("Magicarpe").performClick()
        assertEquals(129, opened)
    }

    @Test
    fun landTimesShareOnePokemonAndKeepTheirChances() {
        val morning = encounter("walk", 20.0).copy(
            times = setOf(
                org.opensources.pokmaps.domain.model.EncounterTime.MORNING
            )
        )
        val night = morning.copy(
            chance = 40.0,
            times = setOf(
                org.opensources.pokmaps.domain.model.EncounterTime.NIGHT
            )
        )
        compose.setContent {
            EncounterGroups(listOf(morning, night).groupByMethod(), title = { it.pokemonName })
        }
        compose.onAllNodesWithText("Magicarpe").assertCountEquals(1)
        compose.onNodeWithContentDescription("Horaire de rencontre : Matin", useUnmergedTree = true).assertExists()
        compose.onNodeWithContentDescription("Horaire de rencontre : Nuit", useUnmergedTree = true).assertExists()
        compose.onNodeWithContentDescription("Horaire de rencontre : Jour : Indisponible").assertExists()
        compose.onNodeWithText("N. 5 \u00e0 10 \u00b7 20 %", useUnmergedTree = true).assertExists()
        compose.onNodeWithText("N. 5 \u00e0 10 \u00b7 40 %", useUnmergedTree = true).assertExists()
    }

    @Test
    fun treeVariantsShareOnePokemonAndKeepTheirMethods() {
        val normal = encounter("headbutt-normal", 20.0)
        val high = encounter("headbutt-high", 40.0)
        val groups = listOf(normal, high).groupByMethod()
        assertEquals(1, groups.size)
        compose.setContent { EncounterGroups(groups, title = { it.pokemonName }) }
        compose.onAllNodesWithText("Magicarpe").assertCountEquals(1)
        compose.onNodeWithContentDescription("headbutt-normal", useUnmergedTree = true).assertExists()
        compose.onNodeWithContentDescription("headbutt-high", useUnmergedTree = true).assertExists()
        compose.onNodeWithText("headbutt-normal").assertDoesNotExist()
        compose.onNodeWithText("headbutt-high").assertDoesNotExist()
        compose.onNodeWithText("Coup d\u2019Boule sur les arbres").assertExists()
    }

    private fun encounter(method: String, chance: Double) = Encounter(
        1, "Rouge", 1, "Route", 129, "Magicarpe", method, method, 1, false,
        5, 10, chance, 1, null, null
    )
}

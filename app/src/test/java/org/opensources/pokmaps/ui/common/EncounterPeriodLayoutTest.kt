package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.width
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.SemanticsActions
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performSemanticsAction
import androidx.compose.ui.text.TextLayoutResult
import androidx.compose.ui.unit.dp
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.EncounterTime
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.domain.model.groupByMethod
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class EncounterPeriodLayoutTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun sinnohLevelAndChancePairsFitOneLineAboveThePokemon() {
        val encounters = listOf(encounter(2, 2, 24.0), encounter(2, 3, 11.0), encounter(3, 3, 10.0))
        compose.setContent {
            Box(Modifier.width(360.dp)) {
                EncounterGroups(
                    encounters.groupByMethod(),
                    title = { it.pokemonName },
                    spritePlace = SpritePlace.MAP_LIST
                )
            }
        }
        compose.onAllNodesWithText("\u00c9tourmi").assertCountEquals(1)
        val pokemon = compose.onNodeWithText("\u00c9tourmi", useUnmergedTree = true).fetchSemanticsNode().boundsInRoot
        val period = compose.onNodeWithText(
            "N. 2 \u00b7 24 %",
            useUnmergedTree = true
        ).fetchSemanticsNode().boundsInRoot
        assertTrue(period.bottom < pokemon.top)
        assertSingleLine("N. 2 \u00b7 24 %")
        assertSingleLine("N. 2 \u00e0 3 \u00b7 11 %")
        assertSingleLine("N. 3 \u00b7 10 %")
    }

    private fun assertSingleLine(text: String) {
        val layouts = mutableListOf<TextLayoutResult>()
        compose.onNodeWithText(text).performSemanticsAction(SemanticsActions.GetTextLayoutResult) { getLayout ->
            assertTrue(getLayout(layouts))
        }
        assertEquals(1, layouts.single().lineCount)
    }

    private fun encounter(min: Int, max: Int, chance: Double) = Encounter(
        12, "Diamant", 1, "Route 201", 396, "\u00c9tourmi", "walk", "Marche", 1, false,
        min, max, chance, 1, null, null, setOf(EncounterTime.MORNING)
    )
}

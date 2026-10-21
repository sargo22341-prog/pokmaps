package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.layout.Column
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.hasContentDescription
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.GameVersion
import org.opensources.pokmaps.domain.model.groupByMethod
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class EncounterGenerationLayoutTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun gameBoyAndGbaEncountersShowLevelsAndChancesOnceWithoutTimeIcons() {
        val versions = listOf(
            GameVersion.RED,
            GameVersion.BLUE,
            GameVersion.YELLOW,
            GameVersion.RUBY,
            GameVersion.SAPPHIRE,
            GameVersion.EMERALD,
            GameVersion.FIRERED,
            GameVersion.LEAFGREEN
        )
        compose.setContent {
            Column {
                versions.forEach { version ->
                    EncounterGroups(listOf(encounter(version, "walk")).groupByMethod(), { it.pokemonName })
                    EncounterGroups(listOf(encounter(version, "surf")).groupByMethod(), { it.pokemonName })
                }
            }
        }
        compose.onAllNodes(hasContentDescription("Horaire de rencontre", substring = true), useUnmergedTree = true)
            .assertCountEquals(0)
        compose.onAllNodesWithText("N. 5 \u00b7 20 %", useUnmergedTree = true).assertCountEquals(versions.size)
        compose.onAllNodesWithText("20 %", useUnmergedTree = true).assertCountEquals(versions.size)
    }

    @Test
    fun johtoAndSinnohKeepTheirTimeIconsEvenForAnAllDayEncounter() {
        val versions = listOf(
            GameVersion.GOLD,
            GameVersion.SILVER,
            GameVersion.CRYSTAL,
            GameVersion.DIAMOND,
            GameVersion.PEARL,
            GameVersion.PLATINUM
        )
        compose.setContent {
            Column {
                versions.forEach { version ->
                    EncounterGroups(listOf(encounter(version, "walk")).groupByMethod(), { it.pokemonName })
                    EncounterTimeIcons(encounter(version, "surf"))
                }
            }
        }
        compose.onAllNodes(hasContentDescription("Horaire de rencontre", substring = true), useUnmergedTree = true)
            .assertCountEquals(versions.size * 6)
    }

    private fun encounter(version: GameVersion, method: String) = Encounter(
        version.id, version.identifier, 1, "Route", 129, "Magicarpe", method, method, 1, false,
        5, 5, 20.0, 1, null, null
    )
}

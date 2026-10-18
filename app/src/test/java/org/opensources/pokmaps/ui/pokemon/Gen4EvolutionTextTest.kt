package org.opensources.pokmaps.ui.pokemon

import androidx.compose.material3.Text
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.v2.createComposeRule
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.domain.pokemon.EvolutionCondition
import org.opensources.pokmaps.domain.pokemon.EvolutionGender
import org.opensources.pokmaps.domain.pokemon.EvolutionTrigger
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class Gen4EvolutionTextTest {
    @get:Rule val compose = createComposeRule()

    @Test
    fun newRequirementsAreVisibleInFrench() {
        val condition = EvolutionCondition(
            EvolutionTrigger.LEVEL_UP,
            itemName = "Griffe Rasoir",
            heldItem = true,
            timeOfDay = "night",
            knownMoveName = "Pouvoir Antique",
            locationName = "Mont Couronné",
            gender = EvolutionGender.FEMALE,
            partySpeciesName = "Rémoraid"
        )
        compose.setContent { Text(evolutionText(condition)) }
        for (part in listOf(
            "En tenant Griffe Rasoir",
            "nuit",
            "Pouvoir Antique",
            "Mont Couronné",
            "Femelle",
            "Rémoraid"
        )) {
            compose.onNode(hasText(part, substring = true)).assertExists()
        }
    }

    @Test
    fun rockProximityAndCloaksAreKept() {
        val condition = EvolutionCondition(
            EvolutionTrigger.LEVEL_UP,
            locationName = "Route 217",
            nearSpecialRock = true,
            requiredFormName = "Cape Sable",
            evolvedFormName = "Cape Déchet"
        )
        compose.setContent { Text(evolutionText(condition)) }
        for (part in listOf("pierre spéciale", "Route 217", "Cape Sable", "Cape Déchet")) {
            compose.onNode(hasText(part, substring = true)).assertExists()
        }
    }
}

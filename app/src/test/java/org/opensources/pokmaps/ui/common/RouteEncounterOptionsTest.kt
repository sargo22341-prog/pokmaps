package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Text
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.performClick
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.domain.model.Encounter
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class RouteEncounterOptionsTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun giftsReplaceWildPokemonAndRoamersAndCanBeTurnedOff() {
        val encounters = listOf(
            encounter("Wild", "walk"),
            encounter("Gift", "gift-egg"),
            encounter("Roamer", "roaming-grass")
        )
        compose.setContent {
            Column {
                RouteEncounterOptions(1, encounters) { selected ->
                    selected.forEach { Text(it.pokemonName) }
                }
            }
        }
        compose.onNode(hasText("Gift")).assertDoesNotExist()
        compose.onNode(hasText("Pok\u00e9mon offerts")).performClick()
        compose.onNode(hasText("Gift")).assertExists()
        compose.onNode(hasText("Wild")).assertDoesNotExist()
        compose.onNode(hasText("Pok\u00e9mon errants")).performClick()
        compose.onNode(hasText("Gift")).assertDoesNotExist()
        compose.onNode(hasText("Roamer")).assertExists()
        compose.onNode(hasText("Pok\u00e9mon offerts")).performClick()
        compose.onNode(hasText("Gift")).assertExists()
        compose.onNode(hasText("Roamer")).assertDoesNotExist()
        compose.onNode(hasText("Pok\u00e9mon offerts")).performClick()
        compose.onNode(hasText("Wild")).assertExists()
    }

    @Test
    fun cartridgeAndRoamingChoicesReplaceTheVisibleSpecies() {
        val encounters = listOf(
            encounter("Ordinaire", "walk", "slot2-none"),
            encounter("Avec Rubis", "walk", "slot2-ruby"),
            encounter("Errant", "roaming-grass")
        )
        compose.setContent {
            Column {
                RouteEncounterOptions(1, encounters) { selected ->
                    selected.forEach { Text(it.pokemonName) }
                }
            }
        }
        compose.onNode(hasText("Ordinaire")).assertExists()
        compose.onNode(hasText("Avec Rubis")).assertDoesNotExist()
        compose.onNode(hasText("Errant")).assertDoesNotExist()
        compose.onNode(hasText("GBA : aucune cartouche")).performClick()
        compose.onNode(hasText("GBA : Rubis")).performClick()
        compose.onNode(hasText("Ordinaire")).assertDoesNotExist()
        compose.onNode(hasText("Avec Rubis")).assertExists()
        compose.onNode(hasText("Pokémon errants")).performClick()
        compose.onNode(hasText("Avec Rubis")).assertDoesNotExist()
        compose.onNode(hasText("Errant")).assertExists()
        compose.onNode(hasText("GBA : Rubis")).assertDoesNotExist()
    }

    @Test
    fun emptyRouteDoesNotOfferIrrelevantFilters() {
        compose.setContent { RouteEncounterOptions(1, emptyList()) {} }
        compose.onNode(hasText("GBA : aucune cartouche")).assertDoesNotExist()
        compose.onNode(hasText("Pokémon errants")).assertDoesNotExist()
    }

    private fun encounter(name: String, method: String, vararg keys: String) = Encounter(
        12, "Diamant", 1, "Route", 16, name, method, method, 1, false,
        2, 4, 20.0, 1, null, null, conditionKeys = keys.toSet()
    )
}

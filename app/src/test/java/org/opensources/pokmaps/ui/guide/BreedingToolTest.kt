package org.opensources.pokmaps.ui.guide

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextReplacement
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.domain.guide.BreedingCatalog
import org.opensources.pokmaps.domain.guide.GuideTarget
import org.opensources.pokmaps.domain.model.PokedexEntry
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class BreedingToolTest {
    @get:Rule val compose = createComposeRule()

    @Test
    fun nameSelectSearchesSpeciesAndSpriteOpensThePreview() {
        var state by mutableStateOf(
            BreedingUiState(
                loading = false,
                catalog = BreedingCatalog(
                    FakeGameDao.GOLD,
                    listOf(
                        PokedexEntry(1, 1, "Bulbizarre"),
                        PokedexEntry(132, 132, "Métamorph")
                    )
                )
            )
        )
        val selected = mutableListOf<BreedingAction.Species>()
        val previews = mutableListOf<GuideTarget>()
        compose.setContent {
            BreedingSpeciesSelector(1, "Bulbizarre", state, true, { action ->
                when (action) {
                    is BreedingAction.Search -> state = state.copy(query = action.query)
                    is BreedingAction.Species -> selected += action
                    is BreedingAction.Values, BreedingAction.Retry -> Unit
                }
            }, { previews += it })
        }
        compose.onNodeWithContentDescription("Bulbizarre").performClick()
        assertEquals(listOf(GuideTarget.Pokemon(1)), previews)
        compose.onNode(hasText("Bulbizarre")).performClick()
        compose.onNode(hasText("Nom ou numéro du Pokémon")).performTextReplacement("metamorph")
        compose.onNode(hasText("Métamorph")).performClick()
        assertEquals(listOf(BreedingAction.Species(true, 132)), selected)
    }
}

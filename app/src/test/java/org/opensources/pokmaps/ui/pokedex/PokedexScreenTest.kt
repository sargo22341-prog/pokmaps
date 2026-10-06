package org.opensources.pokmaps.ui.pokedex

import android.content.Context
import androidx.compose.ui.semantics.ProgressBarRangeInfo
import androidx.compose.ui.test.hasProgressBarRangeInfo
import androidx.compose.ui.test.hasSetTextAction
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.pokedex.PokedexFilter
import org.robolectric.RobolectricTestRunner

/** États du Pokédex que les parcours ne peuvent pas provoquer : chargement, erreur, liste vide. */
@RunWith(RobolectricTestRunner::class)
class PokedexScreenTest {
    @get:Rule
    val compose = createComposeRule()

    private val context: Context = ApplicationProvider.getApplicationContext()
    private val actions = mutableListOf<PokedexAction>()

    private fun show(state: PokedexUiState) {
        compose.setContent { PokedexScreen(state, onAction = { actions += it }, onOpenPokemon = {}) }
    }

    @Test
    fun loadingShowsOnlyProgress() {
        show(PokedexUiState())
        compose.onNode(hasProgressBarRangeInfo(ProgressBarRangeInfo.Indeterminate)).assertExists()
        compose.onNode(hasSetTextAction()).assertDoesNotExist()
    }

    @Test
    fun failureShowsErrorInsteadOfList() {
        show(PokedexUiState(loading = false, failed = true))
        compose.onNode(hasText(context.getString(R.string.data_load_error))).assertExists()
        compose.onNode(hasSetTextAction()).assertDoesNotExist()
    }

    @Test
    fun emptyResultIsNotAnErrorAndFiltersCanBeReset() {
        show(PokedexUiState(loading = false, filter = PokedexFilter(favoritesOnly = true)))
        compose.onNode(hasText(context.getString(R.string.pokedex_empty))).assertExists()
        compose.onNode(hasText(context.getString(R.string.data_load_error))).assertDoesNotExist()

        // Le bouton est au bout de la rangée de filtres, qui défile horizontalement.
        compose.onNode(hasText(context.getString(R.string.pokedex_filter_reset))).performScrollTo().performClick()
        compose.onNode(hasSetTextAction()).performTextInput("evoli")
        assertEquals(listOf(PokedexAction.ResetFilters, PokedexAction.Search("evoli")), actions)
    }
}

package org.opensources.pokmaps.ui.search

import android.content.Context
import androidx.compose.ui.test.hasSetTextAction
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.Game
import org.robolectric.RobolectricTestRunner

/** Messages de la recherche globale (invitation, aucun résultat, erreur) et ouverture d'un résultat. */
@RunWith(RobolectricTestRunner::class)
class SearchScreenTest {
    @get:Rule
    val compose = createComposeRule()

    private val context: Context = ApplicationProvider.getApplicationContext()
    private val actions = mutableListOf<SearchAction>()
    private val openedPlaces = mutableListOf<String>()
    private val red = Game(1, "red", "Rouge", 1, "red-blue", 1)

    private fun show(state: SearchUiState) {
        compose.setContent {
            SearchScreen(
                state,
                onAction = { actions += it },
                onOpenPokemon = {},
                onOpenItem = {},
                onOpenPlace = { openedPlaces += it },
                onOpenCharacter = {}
            )
        }
    }

    @Test
    fun blankQueryInvitesToSearchInTheSelectedGame() {
        show(SearchUiState(loading = false, game = red))
        compose.onNode(hasText(context.getString(R.string.search_intro, "Rouge"))).assertExists()

        compose.onNode(hasSetTextAction()).performTextInput("bourg")
        assertEquals(listOf(SearchAction.Query("bourg")), actions)
    }

    @Test
    fun noResultIsNotAnError() {
        show(SearchUiState(loading = false, game = red, query = "zzz"))
        compose.onNode(hasText(context.getString(R.string.search_empty))).assertExists()
        compose.onNode(hasText(context.getString(R.string.data_load_error))).assertDoesNotExist()
    }

    @Test
    fun failureShowsError() {
        show(SearchUiState(loading = false, failed = true, query = "bourg"))
        compose.onNode(hasText(context.getString(R.string.data_load_error))).assertExists()
        compose.onNode(hasText(context.getString(R.string.search_empty))).assertDoesNotExist()
    }

    @Test
    fun placeResultOpensItsSheet() {
        val place = PlaceResult("pallet-town", "Bourg Palette", outdoor = true)
        show(SearchUiState(loading = false, game = red, query = "bourg", places = listOf(place)))
        compose.onNode(hasText(context.getString(R.string.search_places, 1))).assertExists()

        compose.onNode(hasText("Bourg Palette")).performClick()
        assertEquals(listOf("pallet-town"), openedPlaces)
    }
}

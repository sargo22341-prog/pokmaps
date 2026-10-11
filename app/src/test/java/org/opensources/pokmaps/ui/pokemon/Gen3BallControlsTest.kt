package org.opensources.pokmaps.ui.pokemon

import android.content.Context
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.performClick
import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.pokemon.CaptureGeneration
import org.opensources.pokmaps.domain.pokemon.CatchStatus
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class Gen3BallControlsTest {
    @get:Rule
    val compose = createComposeRule()

    private val context: Context = ApplicationProvider.getApplicationContext()
    private val actions = mutableListOf<PokemonAction>()

    @Test
    fun gbaControlsReplaceJohtoControls() {
        val state = CatchUiState(
            level = 30,
            hp = HpChoice.FULL,
            status = CatchStatus.NONE,
            probabilities = emptyList(),
            best = null,
            generation = CaptureGeneration.GEN3
        )
        compose.setContent { CatchCalculator(state) { actions += it } }
        compose.onNode(hasText(context.getString(R.string.catch_underwater))).performClick()
        compose.onNode(hasText(context.getString(R.string.catch_already_caught))).performClick()
        assertEquals(listOf(PokemonAction.ToggleUnderwater, PokemonAction.ToggleAlreadyCaught), actions)
        compose.onNode(hasText(context.getString(R.string.catch_elapsed_turns, 0))).assertExists()
        compose.onNode(hasText(context.getString(R.string.catch_note_gen3))).assertExists()
        compose.onNode(hasText(context.getString(R.string.catch_fishing))).assertDoesNotExist()
        compose.onNode(hasText(context.getString(R.string.catch_love_bonus))).assertDoesNotExist()
    }
}

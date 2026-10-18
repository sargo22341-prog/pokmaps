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
import org.opensources.pokmaps.domain.pokemon.CaptureEnvironment
import org.opensources.pokmaps.domain.pokemon.CaptureGeneration
import org.opensources.pokmaps.domain.pokemon.CatchStatus
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class Gen4BallControlsTest {
    @get:Rule
    val compose = createComposeRule()
    private val context: Context = ApplicationProvider.getApplicationContext()
    private val actions = mutableListOf<PokemonAction>()
    private val state = CatchUiState(
        30,
        HpChoice.FULL,
        CatchStatus.NONE,
        emptyList(),
        null,
        CaptureGeneration.GEN4
    )

    @Test
    fun normalBattleOffersTheDsContexts() {
        compose.setContent { CatchCalculator(state) { actions += it } }
        compose.onNode(hasText(context.getString(R.string.catch_night_or_cave))).performClick()
        compose.onNode(hasText(context.getString(R.string.catch_water_terrain))).performClick()
        compose.onNode(hasText(context.getString(R.string.catch_pal_park))).performClick()
        assertEquals(
            listOf(
                PokemonAction.ToggleNightOrCave,
                PokemonAction.ToggleWaterTerrain,
                PokemonAction.SetCaptureEnvironment(CaptureEnvironment.PAL_PARK)
            ),
            actions
        )
        compose.onNode(hasText(context.getString(R.string.catch_underwater))).assertDoesNotExist()
    }

    @Test
    fun marshUsesItsStageWithoutImpossibleHealthChoices() {
        compose.setContent { CatchCalculator(state.copy(environment = CaptureEnvironment.GREAT_MARSH)) {} }
        compose.onNode(hasText(context.getString(R.string.catch_safari_stage, 6))).assertExists()
        compose.onNode(hasText(context.getString(R.string.catch_hp))).assertDoesNotExist()
        compose.onNode(hasText(context.getString(R.string.status_label))).assertDoesNotExist()
    }
}

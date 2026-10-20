package org.opensources.pokmaps.ui.guide

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.Roamers
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class SinnohToolScreenTest {
    @get:Rule val compose = createComposeRule()
    private val context: Context = ApplicationProvider.getApplicationContext()

    @Test
    fun platinumBirdShowsLevelSixtyAndRecordsThenClearsAManualObservation() {
        val selections = mutableListOf<String?>()
        compose.setContent {
            var place by remember { mutableStateOf<String?>(null) }
            RoamerCard(Roamers.choices(14).single { it.pokemonId == 144 }, 14, place) {
                selections += it
                place = it
            }
        }
        compose.onNodeWithText(context.getString(R.string.catch_level, 60)).assertExists()
        val empty = context.getString(R.string.roamer_not_observed)
        compose.onNodeWithText(context.getString(R.string.roamer_observation, empty)).performClick()
        val route = context.getString(R.string.roamer_route, 201)
        compose.onNodeWithText(route).performClick()
        compose.onNodeWithText(context.getString(R.string.roamer_observation, route)).performClick()
        compose.onNodeWithText(empty).performClick()
        assertEquals(listOf("route-201", null), selections)
    }
}

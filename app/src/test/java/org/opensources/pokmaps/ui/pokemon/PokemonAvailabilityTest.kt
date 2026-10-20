package org.opensources.pokmaps.ui.pokemon

import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.test.junit4.v2.createComposeRule
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.data.db.FakeGameDao
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class PokemonAvailabilityTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun missingSpeciesReturnsToThePokedexAfterLoading() {
        val state = mutableStateOf(PokemonUiState())
        var returns = 0
        compose.setContent { UnavailablePokemonEffect(state.value) { returns++ } }
        compose.runOnIdle { assertEquals(0, returns) }
        compose.runOnIdle { state.value = PokemonUiState(loading = false, game = FakeGameDao.RED) }
        compose.runOnIdle { assertEquals(1, returns) }
        compose.runOnIdle { state.value = state.value.copy(writeFailed = true) }
        compose.runOnIdle { assertEquals(1, returns) }
    }

    @Test
    fun loadingErrorsDoNotDismissThePage() {
        var returns = 0
        val failed = PokemonUiState(loading = false, failed = true, game = FakeGameDao.RED)
        compose.setContent {
            UnavailablePokemonEffect(failed) { returns++ }
        }
        compose.runOnIdle { assertEquals(0, returns) }
    }
}

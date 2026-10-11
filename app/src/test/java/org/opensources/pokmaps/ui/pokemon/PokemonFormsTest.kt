package org.opensources.pokmaps.ui.pokemon

import android.content.Context
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.test.core.app.ApplicationProvider
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.R
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class PokemonFormsTest {
    @get:Rule val compose = createComposeRule()
    private val context: Context = ApplicationProvider.getApplicationContext()

    @Test
    fun castformShowsItsFourWeatherForms() {
        compose.setContent { PokemonForms(351, "emerald", shiny = true) }
        listOf(
            R.string.pokemon_form_normal,
            R.string.pokemon_form_sunny,
            R.string.pokemon_form_rainy,
            R.string.pokemon_form_snowy
        ).forEach { label -> compose.onNode(hasText(context.getString(label))).assertExists() }
    }

    @Test
    fun deoxysShowsOnlyTheGameForm() {
        compose.setContent { PokemonForms(386, "leafgreen", shiny = false) }
        compose.onNode(hasText(context.getString(R.string.pokemon_form_defense))).assertExists()
        compose.onNode(hasText(context.getString(R.string.pokemon_form_attack))).assertDoesNotExist()
        compose.onNode(hasText(context.getString(R.string.pokemon_form_normal))).assertDoesNotExist()
    }
}

package org.opensources.pokmaps.ui.pokemon

import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.v2.createComposeRule
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.domain.pokemon.PokemonFormTest
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class PokemonFormsTest {
    @get:Rule val compose = createComposeRule()

    @Test
    fun castformShowsItsFourWeatherForms() {
        val labels = listOf("Forme Normale", "Solaire", "Eau de Pluie", "Blizzard")
        val forms = labels.mapIndexed { index, label -> PokemonFormTest.form("form-$index", label, List(6) { 70 }) }
        compose.setContent { PokemonForms(forms, shiny = true) }
        labels.forEach { label -> compose.onNode(hasText(label)).assertExists() }
    }

    @Test
    fun deoxysShowsOnlyTheGameForm() {
        val form = PokemonFormTest.form("defense", "Forme Défense", List(6) { 50 })
        compose.setContent { PokemonForms(listOf(form), shiny = false) }
        compose.onNode(hasText("Forme Défense")).assertExists()
        compose.onNode(hasText("Forme Attaque")).assertDoesNotExist()
        compose.onNode(hasText("Forme Normale")).assertDoesNotExist()
    }
}

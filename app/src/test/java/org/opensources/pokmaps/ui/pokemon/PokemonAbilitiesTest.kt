package org.opensources.pokmaps.ui.pokemon

import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.v2.createComposeRule
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.domain.pokemon.GenderRatio
import org.opensources.pokmaps.domain.pokemon.PokemonAbility
import org.opensources.pokmaps.domain.pokemon.PokemonTraits
import org.robolectric.RobolectricTestRunner

/** Noms et descriptions français des CSV GBA épinglés, vérifiés aussi par test_gen3_abilities.py. */
@RunWith(RobolectricTestRunner::class)
class PokemonAbilitiesTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun displaysBothAbilitiesAndTheirGameDescriptions() {
        val traits = PokemonTraits(
            heldItems = emptyList(),
            gender = GenderRatio.from(4),
            eggGroups = emptyList(),
            hatchCycles = 20,
            abilities = listOf(
                PokemonAbility("Synchro", "Transfère statuts.", false),
                PokemonAbility("Calque", "Imite la capacité spéciale.", false)
            )
        )
        compose.setContent { Abilities(traits) }
        compose.onNode(hasText("Synchro")).assertExists()
        compose.onNode(hasText("Calque")).assertExists()
        compose.onNode(hasText("Transfère statuts.")).assertExists()
        compose.onNode(hasText("Imite la capacité spéciale.")).assertExists()
    }
}

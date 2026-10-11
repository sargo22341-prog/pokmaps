package org.opensources.pokmaps.domain.pokemon

import org.junit.Assert.assertEquals
import org.junit.Test
import org.opensources.pokmaps.domain.model.Sprites

class PokemonFormTest {
    @Test
    fun deoxysStatsMatchItsDisplayedFormAndPreserveLabels() {
        val identifiers = listOf("hp", "attack", "defense", "special-attack", "special-defense", "speed")
        val normal = identifiers.zip(listOf(50, 150, 50, 150, 50, 150)).map { (id, value) ->
            BaseStat(id, id, value)
        }
        assertEquals(normal, PokemonForm.deoxys("ruby").stats(normal))
        assertEquals(listOf(50, 180, 20, 180, 20, 150), PokemonForm.deoxys("firered").stats(normal).map { it.value })
        assertEquals(listOf(50, 70, 160, 70, 160, 90), PokemonForm.deoxys("leafgreen").stats(normal).map { it.value })
        val speed = PokemonForm.deoxys("emerald").stats(normal)
        assertEquals(listOf(50, 95, 90, 95, 90, 180), speed.map { it.value })
        assertEquals(normal.map { it.name }, speed.map { it.name })
    }

    @Test
    fun deoxysUsesTheGameFormInEverySpriteVariant() {
        val forms = mapOf(
            "ruby" to PokemonForm.DEOXYS_NORMAL,
            "sapphire" to PokemonForm.DEOXYS_NORMAL,
            "emerald" to PokemonForm.DEOXYS_SPEED,
            "firered" to PokemonForm.DEOXYS_ATTACK,
            "leafgreen" to PokemonForm.DEOXYS_DEFENSE
        )
        forms.forEach { (version, form) ->
            assertEquals(listOf(form), PokemonForm.available(386, version))
            listOf(false, true).forEach { animated ->
                listOf(false, true).forEach { shiny ->
                    assertEquals(form.sprite(animated, shiny), Sprites.pokemon(386, animated, shiny, version))
                }
            }
        }
    }

    @Test
    fun castformListsFourWeatherFormsWithDistinctAssets() {
        val forms = PokemonForm.available(351, "emerald")
        assertEquals(4, forms.size)
        assertEquals("sprites/pokemon/static/351.webp", forms.first().sprite(false, false))
        assertEquals("sprites/castform/shiny/animated/snowy.webp", forms.last().sprite(true, true))
        assertEquals(4, forms.map { it.sprite(true, false) }.distinct().size)
        assertEquals(emptyList<PokemonForm>(), PokemonForm.available(327, "emerald"))
    }
}

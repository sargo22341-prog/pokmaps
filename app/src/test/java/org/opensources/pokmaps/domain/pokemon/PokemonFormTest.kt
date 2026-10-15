package org.opensources.pokmaps.domain.pokemon

import org.junit.Assert.assertEquals
import org.junit.Test
import org.opensources.pokmaps.domain.model.Sprites

class PokemonFormTest {
    @Test
    fun aFormFromDataControlsStatsAndEverySpriteVariant() {
        val form = form("custom", "Forme test", listOf(50, 180, 20, 180, 20, 150))
        val original = form.baseStats.keys.map { BaseStat(it, "Libellé $it", 1) }
        assertEquals(listOf(50, 180, 20, 180, 20, 150), form.stats(original).map { it.value })
        assertEquals(original.map { it.name }, form.stats(original).map { it.name })
        listOf(false, true).forEach { animated ->
            listOf(false, true).forEach { shiny ->
                assertEquals(
                    form.sprite(animated, shiny),
                    Sprites.pokemon(form.pokemonId, animated, shiny, mapOf(form.pokemonId to listOf(form)))
                )
            }
        }
    }

    @Test(expected = IllegalArgumentException::class)
    fun aFormWithoutAllStatsIsRejected() {
        form("custom", "Forme test", listOf(50))
    }

    @Test(expected = IllegalArgumentException::class)
    fun aSpriteOutsideAssetsIsRejected() {
        form("../custom", "Forme test", List(6) { 50 })
    }

    companion object {
        fun form(sprite: String, name: String, values: List<Int>): PokemonForm = PokemonForm(
            386,
            "custom-$sprite",
            name,
            "deoxys",
            sprite,
            true,
            listOf("hp", "attack", "defense", "special-attack", "special-defense", "speed").zip(values).toMap()
        )
    }
}

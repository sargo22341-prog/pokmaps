package org.opensources.pokmaps.domain.pokedex

import org.junit.Assert.assertEquals
import org.junit.Test
import org.opensources.pokmaps.domain.model.ObtainMethod
import org.opensources.pokmaps.domain.model.PokedexEntry
import org.opensources.pokmaps.domain.model.PokemonType

class PokedexSearchTest {
    private val normal = PokemonType(1, "normal", "Normal")
    private val poison = PokemonType(4, "poison", "Poison")
    private val water = PokemonType(11, "water", "Eau")
    private val electric = PokemonType(13, "electric", "Électrik")

    private val entries = listOf(
        PokedexEntry(25, 25, "Pikachu", "Pikachu", listOf(electric), setOf(ObtainMethod.WALK)),
        PokedexEntry(29, 29, "Nidoran♀", "Nidoran♀", listOf(poison), setOf(ObtainMethod.WALK)),
        PokedexEntry(32, 32, "Nidoran♂", "Nidoran♂", listOf(poison)),
        PokedexEntry(129, 129, "Magicarpe", "Magikarp", listOf(water), setOf(ObtainMethod.FISHING)),
        PokedexEntry(133, 133, "Évoli", "Eevee", listOf(normal), setOf(ObtainMethod.GIFT))
    )

    private fun search(filter: PokedexFilter) = PokedexSearch.filter(entries, filter).map { it.pokemonId }

    @Test
    fun searchIgnoresAccentsAndCase() {
        assertEquals(listOf(133), search(PokedexFilter(query = "evoli")))
        assertEquals(listOf(133), search(PokedexFilter(query = "  ÉVO ")))
    }

    @Test
    fun searchMatchesEnglishNames() {
        assertEquals(listOf(129), search(PokedexFilter(query = "magikarp")))
    }

    @Test
    fun searchByNumber() {
        assertEquals(listOf(25), search(PokedexFilter(query = "25")))
        assertEquals(listOf(25), search(PokedexFilter(query = "025")))
        assertEquals(listOf(25), search(PokedexFilter(query = "n°25")))
        assertEquals(listOf(25), search(PokedexFilter(query = "#25")))
    }

    @Test
    fun searchGenderSymbols() {
        assertEquals(listOf(29, 32), search(PokedexFilter(query = "nidoran")))
        assertEquals(listOf(29), search(PokedexFilter(query = "nidoran f")))
    }

    @Test
    fun filtersCombine() {
        assertEquals(listOf(29, 32), search(PokedexFilter(typeId = poison.id)))
        assertEquals(listOf(29), search(PokedexFilter(typeId = poison.id, availableOnly = true)))
        assertEquals(listOf(129), search(PokedexFilter(method = ObtainMethod.FISHING)))
        assertEquals(emptyList<Int>(), search(PokedexFilter(query = "pika", method = ObtainMethod.GIFT)))
    }

    @Test
    fun evolutionsOfAvailablePokemonAreAvailable() {
        val methods = obtainMethods(
            encounters = mapOf(133 to setOf(ObtainMethod.GIFT), 1 to setOf(ObtainMethod.GIFT)),
            evolutions = listOf(133 to 134, 1 to 2, 2 to 3, 147 to 148)
        )
        assertEquals(setOf(ObtainMethod.EVOLUTION), methods[134])
        assertEquals(setOf(ObtainMethod.EVOLUTION), methods[3])
        assertEquals(null, methods[148])
    }
}

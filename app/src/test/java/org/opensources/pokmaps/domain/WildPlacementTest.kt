package org.opensources.pokmaps.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.opensources.pokmaps.domain.map.WildPlacement

class WildPlacementTest {
    private val spots = (0 until 20).map { it * 48 to it * 32 }

    @Test
    fun eachPokemonIsDrawnSeveralTimesMoreOftenWhenCommon() {
        // Route 1 : Roucool 55 %, Rattata 45 %, beaucoup de place.
        assertEquals(listOf(4, 4), WildPlacement.copies(listOf(55.0, 45.0), spots = 20))
        // Peu de place : au moins un marqueur chacun, le reste selon la fréquence.
        assertEquals(listOf(3, 1, 1), WildPlacement.copies(listOf(80.0, 10.0, 10.0), spots = 5))
        // Plus de Pokémon que d'emplacements : un seul marqueur chacun.
        assertEquals(listOf(1, 1, 1), WildPlacement.copies(listOf(50.0, 30.0, 20.0), spots = 2))
        // Probabilités inconnues : parts égales.
        assertEquals(listOf(2, 2), WildPlacement.copies(listOf(0.0, 0.0), spots = 4))
    }

    @Test
    fun markersUseDistinctSpotsAndAreReproducible() {
        val placed = WildPlacement.place(listOf("roucool", "rattata"), listOf(55.0, 45.0), spots, 0 to 0, seed = 7)
        assertEquals(8, placed.size)
        assertEquals(8, placed.map { it.x to it.y }.toSet().size)
        assertTrue(placed.all { (it.x to it.y) in spots })
        assertEquals(4, placed.count { it.item == "rattata" })
        assertEquals(placed, WildPlacement.place(listOf("roucool", "rattata"), listOf(55.0, 45.0), spots, 0 to 0, 7))
    }

    @Test
    fun extraMarkersSurroundTheSpotWhenSpaceIsMissing() {
        val placed = WildPlacement.place(listOf("a", "b", "c"), listOf(1.0, 1.0, 1.0), emptyList(), 100 to 100, 1)
        assertEquals(3, placed.size)
        assertEquals(3, placed.map { it.x to it.y }.toSet().size)
        assertEquals(100 to 100, placed.first().let { it.x to it.y })
    }

    @Test
    fun pokemonStayAwayFromObjectsAndCharacters() {
        val grass = listOf(8 to 8, 24 to 8, 56 to 8, 104 to 8)
        val npc = listOf(24 to 24)
        // Assez de place : seuls les emplacements à deux cases au moins du personnage restent.
        assertEquals(listOf(56 to 8, 104 to 8), WildPlacement.awayFrom(grass, npc, minimum = 2))
        // Pas assez : les emplacements les moins encombrés complètent, pour dessiner chaque Pokémon.
        assertEquals(listOf(56 to 8, 104 to 8, 8 to 8), WildPlacement.awayFrom(grass, npc, minimum = 3))
        assertEquals(grass, WildPlacement.awayFrom(grass, emptyList(), minimum = 1))
    }
}

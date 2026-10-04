package org.opensources.pokmaps.domain

import kotlin.math.abs
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.opensources.pokmaps.domain.map.WildPlacement

class WildPlacementTest {
    private val spots = (0 until 20).map { it * 48 to it * 32 }

    @Test
    fun eachPokemonIsDrawnAtLeastOnceWithoutCrowdingTheMap() {
        // Route 1 : Roucool 55 %, Rattata 45 %, de la place : deux marqueurs chacun au plus.
        assertEquals(listOf(2, 2), WildPlacement.copies(listOf(55.0, 45.0), spots = 20))
        // Un marqueur pour quatre emplacements : la copie en plus va au plus fréquent.
        assertEquals(listOf(2, 1, 1), WildPlacement.copies(listOf(80.0, 10.0, 10.0), spots = 16))
        // Peu de place : un seul marqueur chacun.
        assertEquals(listOf(1, 1, 1), WildPlacement.copies(listOf(80.0, 10.0, 10.0), spots = 5))
        assertEquals(listOf(1, 1, 1), WildPlacement.copies(listOf(50.0, 30.0, 20.0), spots = 2))
        // Probabilités inconnues : parts égales.
        assertEquals(listOf(2, 2), WildPlacement.copies(listOf(0.0, 0.0), spots = 16))
        // Grande grotte (mont Sélénite) : pas plus de huit marqueurs en tout…
        assertEquals(WildPlacement.MAX_MARKERS, WildPlacement.copies(List(6) { 1.0 }, spots = 40).sum())
        // … sauf s'il y a davantage de Pokémon différents.
        assertEquals(List(10) { 1 }, WildPlacement.copies(List(10) { 1.0 }, spots = 40))
    }

    @Test
    fun markersUseDistinctSpotsAndAreReproducible() {
        val placed = WildPlacement.place(listOf("roucool", "rattata"), listOf(55.0, 45.0), spots, 0 to 0, seed = 7)
        assertEquals(4, placed.size)
        assertEquals(4, placed.map { it.x to it.y }.toSet().size)
        assertTrue(placed.all { (it.x to it.y) in spots && it.scale == 1f })
        assertEquals(2, placed.count { it.item == "rattata" })
        assertEquals(placed, WildPlacement.place(listOf("roucool", "rattata"), listOf(55.0, 45.0), spots, 0 to 0, 7))
    }

    @Test
    fun markersAreSpreadOverTheTerrain() {
        // Les deux marqueurs d'un Pokémon sur une ligne d'emplacements : loin l'un de l'autre, pas côte à côte.
        val line = (0 until 12).map { it * 48 to 0 }
        val placed = WildPlacement.place(listOf("a"), listOf(1.0), line, 0 to 0, seed = 3)
        assertEquals(2, placed.size)
        assertTrue(abs(placed[0].x - placed[1].x) >= 6 * 48)
    }

    @Test
    fun pokemonAreLinedUpSmallerOnNarrowTerrain() {
        // Petit étang : un seul emplacement pour quatre Pokémon pêchés, rangés en carré autour de lui.
        val pond = WildPlacement.place(listOf("a", "b", "c", "d"), List(4) { 1.0 }, listOf(100 to 100), 0 to 0, 1)
        assertEquals(listOf(86 to 86, 114 to 86, 86 to 114, 114 to 114), pond.map { it.x to it.y })
        assertTrue(pond.all { it.scale == WildPlacement.CROWDED_SCALE })
        // Sans emplacement, autour du point de repli ; la dernière ligne est centrée.
        val placed = WildPlacement.place(listOf("a", "b", "c"), List(3) { 1.0 }, emptyList(), 100 to 100, 1)
        assertEquals(listOf(86 to 86, 114 to 86, 100 to 114), placed.map { it.x to it.y })
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

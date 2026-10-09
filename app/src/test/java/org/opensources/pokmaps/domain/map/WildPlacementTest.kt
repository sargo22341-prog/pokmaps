package org.opensources.pokmaps.domain.map

import kotlin.math.abs
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class WildPlacementTest {
    private val spots = (0 until 20).map { it * 48 to it * 32 }

    @Test
    fun eachPokemonIsDrawnAtLeastOnceWithoutCrowdingTheMap() {
        // Route 1 : Roucool 55 %, Rattata 45 %, de la place : deux marqueurs chacun au plus.
        assertEquals(listOf(2, 2), WildPlacement.copies(listOf(55.0, 45.0), room = 20))
        // Place pour quatre marqueurs : la copie en plus va au plus fréquent.
        assertEquals(listOf(2, 1, 1), WildPlacement.copies(listOf(80.0, 10.0, 10.0), room = 4))
        // Peu de place : un seul marqueur chacun.
        assertEquals(listOf(1, 1, 1), WildPlacement.copies(listOf(80.0, 10.0, 10.0), room = 3))
        assertEquals(listOf(1, 1, 1), WildPlacement.copies(listOf(50.0, 30.0, 20.0), room = 0))
        // Probabilités inconnues : parts égales.
        assertEquals(listOf(2, 2), WildPlacement.copies(listOf(0.0, 0.0), room = 4))
        // Grande grotte (mont Sélénite) : pas plus de huit marqueurs en tout…
        assertEquals(WildPlacement.MAX_MARKERS, WildPlacement.copies(List(6) { 1.0 }, room = 40).sum())
        // … sauf s'il y a davantage de Pokémon différents.
        assertEquals(List(10) { 1 }, WildPlacement.copies(List(10) { 1.0 }, room = 40))
    }

    @Test
    fun markerSizeFollowsTheRoomOnTheTerrain() {
        // Grand terrain, deux Pokémon : taille normale, et des copies.
        val large = (0 until 40).map { (it % 8) * 48 to (it / 8) * 48 }
        val roomy = WildPlacement.place(listOf("a", "b"), listOf(1.0, 1.0), large, seed = 1)
        assertEquals(4, roomy.size)
        assertTrue(roomy.all { it.scale == 1f })
        // Petit plan d'eau de grotte (Caverne Azurée : 10 emplacements) et huit Pokémon : un chacun, réduits.
        val pool = (0 until 10).map { it * 48 to 0 }
        val crowded = WildPlacement.place(List(8) { "p$it" }, List(8) { 1.0 }, pool, seed = 1)
        assertEquals(8, crowded.size)
        assertEquals(1, crowded.map { it.scale }.toSet().size)
        assertTrue(crowded[0].scale < 0.6f && crowded[0].scale >= MarkerSizing.MIN_SCALE)
        // Plus il y a de Pokémon sur un même terrain, plus ils sont petits.
        val few = WildPlacement.place(List(3) { "p$it" }, List(3) { 1.0 }, pool, seed = 1)
        assertTrue(few[0].scale > crowded[0].scale)
    }

    @Test
    fun markersUseDistinctSpotsAndAreReproducible() {
        val placed = WildPlacement.place(listOf("roucool", "rattata"), listOf(55.0, 45.0), spots, seed = 7)
        // Place pour trois marqueurs : la copie va au plus fréquent.
        assertEquals(3, placed.size)
        assertEquals(3, placed.map { it.x to it.y }.toSet().size)
        assertTrue(placed.all { (it.x to it.y) in spots })
        assertEquals(2, placed.count { it.item == "roucool" })
        assertEquals(placed, WildPlacement.place(listOf("roucool", "rattata"), listOf(55.0, 45.0), spots, 7))
    }

    @Test
    fun markersAreSpreadOverTheTerrain() {
        // Les deux marqueurs d'un Pokémon sur une ligne d'emplacements : loin l'un de l'autre, pas côte à côte.
        val line = (0 until 30).map { it * 48 to 0 }
        val placed = WildPlacement.place(listOf("a"), listOf(1.0), line, seed = 3)
        assertEquals(2, placed.size)
        assertTrue(abs(placed[0].x - placed[1].x) >= 15 * 48)
    }

    @Test
    fun narrowTerrainShowsOneRandomPokemonPerSpot() {
        // Petit étang : deux emplacements pour quatre Pokémon pêchés, un seul par emplacement.
        val pond = listOf(100 to 100, 200 to 100)
        val items = listOf("a", "b", "c", "d")
        val placed = WildPlacement.place(items, List(4) { 1.0 }, pond, seed = 1)
        assertEquals(pond, placed.map { it.x to it.y })
        assertEquals(2, placed.map { it.item }.toSet().size)
        assertTrue(placed.all { it.item in items })
        assertEquals(1, placed.map { it.scale }.toSet().size)
        // Tirage reproductible.
        assertEquals(placed, WildPlacement.place(items, List(4) { 1.0 }, pond, seed = 1))
        // Sans emplacement, rien n'est dessiné : les Pokémon restent dans la liste du lieu.
        assertTrue(WildPlacement.place(items, List(4) { 1.0 }, emptyList(), seed = 1).isEmpty())
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

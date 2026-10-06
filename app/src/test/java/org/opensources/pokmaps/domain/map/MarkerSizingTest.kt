package org.opensources.pokmaps.domain.map

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class MarkerSizingTest {
    @Test
    fun markersShrinkWithTheNumberOfPokemonAndGrowWithTheTerrain() {
        val area = MarkerSizing.terrainArea(spots = 10)
        val one = MarkerSizing.coverageScale(area, 1, Footprint.POKEMON)
        val eight = MarkerSizing.coverageScale(area, 8, Footprint.POKEMON)
        assertEquals(1f, one)
        assertTrue(eight < one)
        assertTrue(MarkerSizing.coverageScale(area * 4, 8, Footprint.POKEMON) > eight)
        // Jamais plus petit que le minimum, même sans place du tout.
        assertEquals(MarkerSizing.MIN_SCALE, MarkerSizing.coverageScale(0.0, 8, Footprint.POKEMON))
        assertEquals(0, MarkerSizing.capacity(0.0, Footprint.POKEMON))
    }

    @Test
    fun markersDoNotOverlap() {
        // Deux Pokémon à 21 pixels l'un de l'autre : moitié de leur largeur (42 pixels).
        assertEquals(0.5f, MarkerSizing.spacingScale(listOf(0 to 0, 21 to 0), Footprint.POKEMON))
        // Écartés sur l'autre axe : c'est la hauteur qui compte.
        assertEquals(0.5f, MarkerSizing.spacingScale(listOf(0 to 0, 0 to 22), Footprint.POKEMON))
        assertEquals(1f, MarkerSizing.spacingScale(listOf(0 to 0, 100 to 0), Footprint.POKEMON))
        assertEquals(1f, MarkerSizing.spacingScale(listOf(0 to 0), Footprint.POKEMON))
    }

    @Test
    fun fixedMarkersShareOneSizeFromTheirSurroundings() {
        // Personnages à une case d'écart : taille normale (un personnage fait une case).
        val row = (0 until 4).map { it * 16 to 0 }
        assertEquals(1f, MarkerSizing.crowdScale(row, row, Footprint.CHARACTER))
        // Objets serrés (une case d'écart) : réduits, tous de la même taille.
        assertEquals(16 / 24f, MarkerSizing.crowdScale(row, row, Footprint.ITEM), 0.001f)
        // Un seul objet collé à un personnage ne réduit pas tous les autres objets.
        val items = listOf(0 to 0, 200 to 0, 400 to 0, 600 to 0)
        assertEquals(1f, MarkerSizing.crowdScale(items, items + (16 to 0), Footprint.ITEM))
        assertEquals(1f, MarkerSizing.crowdScale(emptyList(), emptyList(), Footprint.ITEM))
    }

    @Test
    fun objectsOfAPlaceAreSizedTogether() {
        fun obj(id: Int, mapId: Int, x: Int, item: String? = null) =
            MapObject(id, mapId, MapObjectKind.ITEM, x, 0, null, null, item, null, null, null, null, null, "Potion")
        // Objets à une case l'un de l'autre dans un lieu, bien espacés dans l'autre.
        val tight = (0 until 4).map { obj(it, mapId = 1, x = it * 16, item = "potion") }
        val loose = (0 until 4).map { obj(10 + it, mapId = 2, x = it * 100, item = "potion") }
        val scales = MarkerSizing.objectScales(tight + loose)
        assertEquals(setOf(16 / 24f), tight.map { scales.getValue(it.id) }.toSet())
        assertEquals(setOf(1f), loose.map { scales.getValue(it.id) }.toSet())
        // Sans icône d'objet : sprite d'une case, à sa taille normale à une case d'écart.
        assertEquals(Footprint.CHARACTER, MarkerSizing.footprintOf(obj(20, mapId = 3, x = 0)))
    }
}

package org.opensources.pokmaps.domain.model

import org.junit.Assert.assertEquals
import org.junit.Test

class EncounterHabitatTest {
    @Test
    fun caveAndIceRoomsUseTheirOwnTerrainAcrossGenerations() {
        for (location in listOf("mt-moon", "dark-cave", "tohjo-falls", "granite-cave", "mt-coronet")) {
            assertEquals(EncounterHabitat.CAVE, EncounterHabitat.of(location, "1f", "walk"))
            assertEquals(EncounterHabitat.CAVE, EncounterHabitat.of(location, "1f", "surf"))
        }
        for (location in listOf("ice-path", "icefall-cave", "seafoam-islands", "snowpoint-temple")) {
            assertEquals(EncounterHabitat.ICE, EncounterHabitat.of(location, "1f", "walk"))
        }
        assertEquals(EncounterHabitat.ICE, EncounterHabitat.of("shoal-cave", "b3f", "walk"))
        assertEquals(EncounterHabitat.CAVE, EncounterHabitat.of("shoal-cave", "low-tide", "walk"))
    }

    @Test
    fun outdoorPartsOfMountainsAreNotCaves() {
        for ((location, area) in listOf("mt-silver" to "outside", "mt-coronet" to "north-mountainside")) {
            assertEquals(EncounterHabitat.TALL_GRASS, EncounterHabitat.of(location, area, "walk"))
            assertEquals(EncounterHabitat.GRASS, EncounterHabitat.of(location, area, "old-rod"))
        }
        assertEquals(EncounterHabitat.GRASS, EncounterHabitat.of("iron-island", "", "surf"))
        assertEquals(EncounterHabitat.CAVE, EncounterHabitat.of("iron-island", "b1f-left", "walk"))
    }

    @Test
    fun treesDesertAndIndoorFloorsDoNotUseTallGrass() {
        for (method in listOf("headbutt", "headbutt-low", "headbutt-normal", "headbutt-high", "honey-tree")) {
            assertEquals(EncounterHabitat.FOREST, EncounterHabitat.of("johto-route-29", "", method))
        }
        assertEquals(EncounterHabitat.SAND, EncounterHabitat.of("hoenn-route-111", "", "walk"))
        assertEquals(EncounterHabitat.FLOOR, EncounterHabitat.of("pokemon-tower", "3f", "walk"))
        assertEquals(EncounterHabitat.FLOOR, EncounterHabitat.of("mt-pyre", "3f", "walk"))
        assertEquals(EncounterHabitat.TALL_GRASS, EncounterHabitat.of("mt-pyre", "outside", "walk"))
    }
}

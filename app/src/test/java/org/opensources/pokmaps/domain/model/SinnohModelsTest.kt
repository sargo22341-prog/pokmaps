package org.opensources.pokmaps.domain.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.domain.map.MapDestinations

class SinnohModelsTest {
    @Test
    fun cartridgeIdentitiesAndRegionsAreExplicit() {
        assertEquals(Generation.GEN4, Generation.of(4))
        assertEquals(493, Generation.GEN4.maximumSpecies)
        listOf(FakeGameDao.DIAMOND, FakeGameDao.PEARL, FakeGameDao.PLATINUM).forEach { game ->
            assertEquals(game.versionIdentifier, game.version.identifier)
            assertEquals(Generation.GEN4, game.version.generation)
            assertEquals(game.versionGroupIdentifier, game.version.group.identifier)
            assertEquals(game.versionGroupIdentifier, game.mapFamily)
            assertEquals("sinnoh", MapDestinations.startRegion(game.versionGroup))
        }
    }

    @Test
    fun honeyTreesHaveTheirOwnPlaceFilter() {
        val honey = Encounter(
            14, "Platine", 1, "Route 205", 415, "Apitrini", "honey-tree", "Arbre à Miel",
            1, false, 5, 15, 20.0, 1, null, null
        )
        assertTrue(honey.isWild)
        assertTrue(EncounterFilter.HONEY_TREE.matches(honey))
        assertFalse(EncounterFilter.WALK.matches(honey))
        assertFalse(EncounterFilter.HONEY_TREE.matches(honey.copy(method = "walk")))
        assertTrue(EncounterFilter.ALL.matches(honey))
    }
}

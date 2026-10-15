package org.opensources.pokmaps.domain.model

import org.junit.Assert.assertEquals
import org.junit.Test

class GameVersionTest {
    @Test
    fun everyVersionHasAUniqueIdentifierAndSupportedGeneration() {
        assertEquals(11, GameVersion.entries.map { it.id }.toSet().size)
        assertEquals(11, GameVersion.entries.map { it.identifier }.toSet().size)
        GameVersion.entries.forEach {
            assertEquals(it, GameVersion.of(it.id))
            assertEquals(it, GameVersion.of(it.identifier))
            assertEquals(it.generation, Generation.of(it.generation.id))
        }
    }

    @Test(expected = IllegalArgumentException::class)
    fun aNewGenerationRequiresExplicitRules() {
        Generation.of(4)
    }

    @Test(expected = IllegalArgumentException::class)
    fun aNewVersionRequiresExplicitRules() {
        GameVersion.of(12)
    }
}

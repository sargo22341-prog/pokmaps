package org.opensources.pokmaps.data.settings

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.domain.guide.CollectionBackup
import org.opensources.pokmaps.domain.guide.GuideProgress
import org.opensources.pokmaps.domain.guide.RoamerObservation
import org.opensources.pokmaps.domain.pokemon.UnownForm
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class BackupJsonTest {
    @Test
    fun roundTripPreservesEachVersionAndContainsNoCredentials() {
        val backup = CollectionBackup(
            setOf(25),
            mapOf(1 to setOf(25), 2 to setOf(133)),
            mapOf(
                4 to GuideProgress(setOf("ra-5070"), listOf(RoamerObservation(243, "route-29")))
            )
        )
        val withForms = backup.copy(unown = mapOf(4 to setOf(UnownForm.A, UnownForm.Z)))
        val text = BackupJson.encode(withForms)
        val decoded = BackupJson.decode(text)
        assertEquals(backup.favorites, decoded.favorites)
        assertEquals(backup.caught[1], decoded.caught[1])
        assertEquals(backup.caught[2], decoded.caught[2])
        assertEquals(backup.guides[4], decoded.guides[4])
        assertEquals(withForms.unown, decoded.unown)
        assertFalse(text.contains("apiKey") || text.contains("username") || text.contains("retro_"))
    }

    @Test
    fun importingMergesCapturesAndUsesTheIncomingLastObservation() {
        val current = CollectionBackup(
            setOf(25),
            mapOf(1 to setOf(25)),
            mapOf(
                4 to GuideProgress(
                    setOf("johto-start"),
                    listOf(RoamerObservation(243, "route-29"), RoamerObservation(244, "route-30"))
                )
            )
        )
        val imported = CollectionBackup(
            setOf(133),
            mapOf(1 to setOf(1), 2 to setOf(7)),
            mapOf(
                4 to GuideProgress(
                    setOf("ra-5070"),
                    listOf(RoamerObservation(243, "route-42"))
                )
            )
        )
        val merged = merge(current, imported)
        assertEquals(setOf(1, 25), merged.caught[1])
        assertEquals(setOf(7), merged.caught[2])
        assertEquals(setOf(25, 133), merged.favorites)
        assertEquals(setOf("johto-start", "ra-5070"), merged.guides[4]?.completed)
        assertEquals("route-42", merged.guides[4]?.roamers?.single { it.pokemonId == 243 }?.place)
        assertEquals("route-30", merged.guides[4]?.roamers?.single { it.pokemonId == 244 }?.place)
    }

    @Test(expected = IllegalArgumentException::class)
    fun unknownSchemaIsRejected() {
        BackupJson.decode("""{"format":"pokmaps-collection","schema":2,"favorites":[],"games":[]}""")
    }

    @Test(expected = IllegalArgumentException::class)
    fun outOfGenerationPokemonIsRejected() {
        BackupJson.decode(
            """{"format":"pokmaps-collection","schema":1,"favorites":[],"games":[
            {"version":1,"caught":[251],"completed":[],"roamers":[]}
        ]}"""
        )
    }

    @Test(expected = IllegalArgumentException::class)
    fun fractionalPokemonIdsAreRejected() {
        BackupJson.decode("""{"format":"pokmaps-collection","schema":1,"favorites":[25.5],"games":[]}""")
    }

    @Test(expected = IllegalArgumentException::class)
    fun punctuationUnownCannotBeImportedIntoGenerationTwo() {
        BackupJson.decode(
            """{"format":"pokmaps-collection","schema":1,"favorites":[],"games":[
            {"version":4,"caught":[],"completed":[],"roamers":[],"unown":["question"]}
        ]}"""
        )
    }
}

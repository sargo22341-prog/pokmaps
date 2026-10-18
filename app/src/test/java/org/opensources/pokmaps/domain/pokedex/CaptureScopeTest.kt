package org.opensources.pokmaps.domain.pokedex

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import org.opensources.pokmaps.domain.model.Game

class CaptureScopeTest {
    private val red = game(1, generation = 1)
    private val blue = game(2, generation = 1)
    private val gold = game(4, generation = 2)
    private val games = listOf(red, blue, gold)

    // Bulbizarre dans Rouge, Salamèche dans Bleu, Germignon dans Or, et une version qui n'est plus proposée.
    private val caught = mapOf(1 to setOf(1), 2 to setOf(4), 4 to setOf(152), 99 to setOf(7))

    @Test
    fun gameCountsOnlyItsOwnCaptures() {
        assertEquals(setOf(1), CaptureScope.GAME.caught(red, games, caught))
    }

    @Test
    fun generationCountsTheCapturesOfItsGames() {
        assertEquals(setOf(1, 4), CaptureScope.GENERATION.caught(red, games, caught))
        assertEquals(setOf(152), CaptureScope.GENERATION.caught(gold, games, caught))
    }

    @Test
    fun allCountsEveryRecordedCapture() {
        assertEquals(setOf(1, 4, 152, 7), CaptureScope.ALL.caught(blue, games, caught))
    }

    @Test
    fun versionsToClearFollowTheScope() {
        assertEquals(setOf(1), CaptureScope.GAME.versionsFor(red, games, caught.keys))
        assertEquals(setOf(1, 2), CaptureScope.GENERATION.versionsFor(red, games, caught.keys))
        assertEquals(setOf(1, 2, 4, 99), CaptureScope.ALL.versionsFor(red, games, caught.keys))
    }

    @Test
    fun sinnohGenerationSharesItsThreeVersionsWithoutHoenn() {
        val emerald = game(9, generation = 3)
        val diamond = game(12, generation = 4)
        val pearl = game(13, generation = 4)
        val platinum = game(14, generation = 4)
        val catalog = listOf(emerald, diamond, pearl, platinum)
        val captures = mapOf(9 to setOf(384), 12 to setOf(483), 13 to setOf(484), 14 to setOf(487, 493))

        for ((version, pokemon) in listOf(diamond to 483, pearl to 484, platinum to 487)) {
            val own = if (version == platinum) setOf(pokemon, 493) else setOf(pokemon)
            assertEquals(own, CaptureScope.GAME.caught(version, catalog, captures))
            assertEquals(setOf(483, 484, 487, 493), CaptureScope.GENERATION.caught(version, catalog, captures))
            assertEquals(setOf(12, 13, 14), CaptureScope.GENERATION.versionsFor(version, catalog, captures.keys))
            assertEquals(setOf(384, 483, 484, 487, 493), CaptureScope.ALL.caught(version, catalog, captures))
        }
        assertEquals(setOf(384), CaptureScope.GENERATION.caught(emerald, catalog, captures))
    }

    @Test
    fun identifiersRoundTrip() {
        CaptureScope.entries.forEach { assertEquals(it, CaptureScope.fromIdentifier(it.identifier)) }
        assertNull(CaptureScope.fromIdentifier("inconnu"))
    }

    private fun game(versionId: Int, generation: Int) =
        Game(versionId, "v$versionId", "Version $versionId", versionId, "vg$versionId", generation, 25, 0)
}

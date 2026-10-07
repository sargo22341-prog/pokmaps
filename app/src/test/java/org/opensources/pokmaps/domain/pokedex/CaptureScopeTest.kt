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
    fun identifiersRoundTrip() {
        CaptureScope.entries.forEach { assertEquals(it, CaptureScope.fromIdentifier(it.identifier)) }
        assertNull(CaptureScope.fromIdentifier("inconnu"))
    }

    private fun game(versionId: Int, generation: Int) =
        Game(versionId, "v$versionId", "Version $versionId", versionId, "vg$versionId", generation, 25, 0)
}

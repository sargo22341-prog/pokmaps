package org.opensources.pokmaps.data.retro

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class RetroApiTest {
    @Test
    fun emptyProgressIsValidAndHardcoreAlsoCountsAsEarned() {
        assertEquals(RetroUnlocks(emptySet(), emptySet()), parseRetroProgress("""{"ID":724,"Achievements":{}}""", 724))
        val text = """{"ID":724,"Achievements":{
            "1":{"ID":1,"DateEarned":"2026-01-01"},
            "2":{"ID":2,"DateEarnedHardcore":"2026-01-01"},
            "3":{"ID":3,"DateEarned":null}
        }}"""
        assertEquals(RetroUnlocks(setOf(1, 2), setOf(2)), parseRetroProgress(text, 724))
    }

    @Test(expected = IllegalArgumentException::class)
    fun wrongGameCannotPolluteTheCache() {
        parseRetroProgress("""{"ID":586,"Achievements":{}}""", 724)
    }

    @Test(expected = IllegalArgumentException::class)
    fun mismatchedAchievementIdIsRejected() {
        parseRetroProgress("""{"ID":724,"Achievements":{"1":{"ID":2}}}""", 724)
    }

    @Test
    fun accountNeverIncludesTheKeyInItsStringRepresentation() {
        val secret = "a".repeat(32)
        assertFalse(RetroAccount("player", secret).toString().contains(secret))
    }
}

package org.opensources.pokmaps.domain.guide

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class HgssFriendshipTest {
    private val rules = FriendshipRules.HEARTGOLD_SOULSILVER

    @Test
    fun bonusesPrecedeBellForItemsAndOrdinaryEventsAcrossAllBands() {
        for (event in listOf(FriendshipEvent.LEVEL, FriendshipEvent.VITAMIN, FriendshipEvent.EV_BERRY)) {
            for (value in listOf(0, 99, 100, 199, 200, 254, 255)) {
                val delta = (event.delta(value) + 2) * 150 / 100
                assertEquals((value + delta).coerceAtMost(255), rules.apply(event, value, true, true, true))
            }
        }
        assertEquals(110, rules.apply(FriendshipEvent.EV_BERRY, 100, true, true, true))
        assertEquals(210, rules.apply(FriendshipEvent.X_ITEM, 210, true, true, true))
        assertEquals(0, rules.apply(FriendshipEvent.REVIVAL_HERB, 1, true, true, true))
        assertEquals(190, rules.apply(FriendshipEvent.BITTER_POWDER, 200, true, true, true))
    }

    @Test
    fun nativeGroomingResultsHaveBonusesButSinnohServicesAreUnavailable() {
        for (event in listOf(
            FriendshipEvent.HGSS_GROOM_SMALL,
            FriendshipEvent.HGSS_GROOM_MEDIUM,
            FriendshipEvent.HGSS_GROOM_LARGE
        )) {
            assertTrue(event in rules.events)
            assertFalse(event in FriendshipRules.SINNOH.events)
            assertEquals(100 + (event.medium + 2) * 150 / 100, rules.apply(event, 100, true, true, true))
        }
        assertFalse(FriendshipEvent.CONTEST in rules.events)
        assertFalse(FriendshipEvent.SPA in rules.events)
        assertFalse(FriendshipEvent.LEVEL_AT_CAPTURE_PLACE in rules.events)
    }
}

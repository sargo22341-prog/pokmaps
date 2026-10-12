package org.opensources.pokmaps.domain.guide

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class FriendshipRulesTest {
    @Test
    fun positiveBonusesAreRoundedBeforeLocationAndBallAndNeverAffectLosses() {
        val rules = FriendshipRules.EMERALD
        assertEquals(106, rules.apply(FriendshipEvent.LEVEL, 100, true, true, true))
        assertEquals(104, rules.apply(FriendshipEvent.LEVEL, 100, false, true, false))
        assertEquals(210, rules.apply(FriendshipEvent.X_ITEM, 210, true, true, true))
        assertEquals(200, rules.apply(FriendshipEvent.POISON_FAINT, 210, true, true, true))
        assertEquals(255, rules.apply(FriendshipEvent.LEVEL, 254, true, true, true))
        assertEquals(0, rules.apply(FriendshipEvent.REVIVAL_HERB, 1, true, true, true))
    }

    @Test
    fun branchesHaveTheirOwnEventsAndThresholds() {
        assertTrue(FriendshipEvent.EV_BERRY in FriendshipRules.EMERALD.events)
        assertFalse(FriendshipEvent.EV_BERRY in FriendshipRules.RUBY_SAPPHIRE.events)
        assertTrue(FriendshipEvent.MASSAGE in FriendshipRules.FIRERED_LEAFGREEN.events)
        assertFalse(FriendshipEvent.MASSAGE in FriendshipRules.EMERALD.events)
        assertFalse(FriendshipEvent.GROOMING in FriendshipRules.EMERALD.events)
        assertFalse(FriendshipEvent.LEVEL_AT_CAPTURE_PLACE in FriendshipRules.EMERALD.events)
        val rules = FriendshipRules.EMERALD
        assertEquals(109, rules.apply(FriendshipEvent.EV_BERRY, 99, false, false, false))
        assertEquals(105, rules.apply(FriendshipEvent.EV_BERRY, 100, false, false, false))
        assertEquals(202, rules.apply(FriendshipEvent.EV_BERRY, 200, false, false, false))
    }
}

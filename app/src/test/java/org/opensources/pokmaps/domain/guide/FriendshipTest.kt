package org.opensources.pokmaps.domain.guide

import org.junit.Assert.assertEquals
import org.junit.Test

class FriendshipTest {
    @Test
    fun changesUseTheInitialBandAndClampToTheValidRange() {
        assertEquals(104, FriendshipEvent.LEVEL.apply(99))
        assertEquals(103, FriendshipEvent.LEVEL.apply(100))
        assertEquals(202, FriendshipEvent.LEVEL.apply(199))
        assertEquals(202, FriendshipEvent.LEVEL.apply(200))
        assertEquals(255, FriendshipEvent.LEVEL.apply(254))
        assertEquals(0, FriendshipEvent.REVIVAL_HERB.apply(5))
        assertEquals(200, FriendshipEvent.X_ITEM.apply(200))
        assertEquals(205, FriendshipEvent.LEVEL_AT_CAPTURE_PLACE.apply(199))
    }
}

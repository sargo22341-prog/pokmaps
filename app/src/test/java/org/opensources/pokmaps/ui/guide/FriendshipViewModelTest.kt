package org.opensources.pokmaps.ui.guide

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test
import org.opensources.pokmaps.domain.guide.FriendshipEvent

class FriendshipViewModelTest {
    @Test
    fun crystalSpecificEventCannotLeakIntoGoldAndSilver() {
        val model = FriendshipViewModel()
        model.onAction(FriendshipAction.Crystal(true))
        model.onAction(FriendshipAction.Event(FriendshipEvent.LEVEL_AT_CAPTURE_PLACE))
        assertEquals(FriendshipEvent.LEVEL_AT_CAPTURE_PLACE, model.state.value.event)
        model.onAction(FriendshipAction.Crystal(false))
        assertEquals(FriendshipEvent.LEVEL, model.state.value.event)
        assertFalse(FriendshipEvent.LEVEL_AT_CAPTURE_PLACE in model.state.value.events)
    }

    @Test
    fun invalidSliderValuesAreClampedAndResultUsesTheCurrentBand() {
        val model = FriendshipViewModel()
        model.onAction(FriendshipAction.Value(1000))
        assertEquals(255, model.state.value.value)
        assertEquals(255, model.state.value.result)
        model.onAction(FriendshipAction.Value(199))
        assertEquals(202, model.state.value.result)
    }
}

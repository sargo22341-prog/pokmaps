package org.opensources.pokmaps.ui.guide

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test
import org.opensources.pokmaps.domain.guide.FriendshipEvent
import org.opensources.pokmaps.domain.guide.FriendshipRules

class FriendshipViewModelTest {
    @Test
    fun hgssUsesItsItemOrderAndDropsGroomingWhenChangingGame() {
        val model = FriendshipViewModel()
        model.onAction(FriendshipAction.Rules(FriendshipRules.HEARTGOLD_SOULSILVER))
        model.onAction(FriendshipAction.Value(100))
        model.onAction(FriendshipAction.Event(FriendshipEvent.EV_BERRY))
        model.onAction(FriendshipAction.SootheBell(true))
        model.onAction(FriendshipAction.LuxuryBall(true))
        model.onAction(FriendshipAction.CapturePlace(true))
        assertEquals(110, model.state.value.result)
        model.onAction(FriendshipAction.Event(FriendshipEvent.HGSS_GROOM_LARGE))
        model.onAction(FriendshipAction.Rules(FriendshipRules.SINNOH))
        assertEquals(FriendshipEvent.LEVEL, model.state.value.event)
        assertFalse(model.state.value.sootheBell)
    }

    @Test
    fun changingBranchDropsUnavailableEventsAndBonuses() {
        val model = FriendshipViewModel()
        model.onAction(FriendshipAction.Rules(FriendshipRules.EMERALD))
        model.onAction(FriendshipAction.Event(FriendshipEvent.EV_BERRY))
        model.onAction(FriendshipAction.SootheBell(true))
        model.onAction(FriendshipAction.LuxuryBall(true))
        model.onAction(FriendshipAction.CapturePlace(true))
        assertEquals(87, model.state.value.result)
        model.onAction(FriendshipAction.Rules(FriendshipRules.FIRERED_LEAFGREEN))
        assertEquals(FriendshipEvent.LEVEL, model.state.value.event)
        assertEquals(75, model.state.value.result)
        model.onAction(FriendshipAction.Event(FriendshipEvent.EV_BERRY))
        assertEquals(FriendshipEvent.LEVEL, model.state.value.event)
    }

    @Test
    fun crystalSpecificEventCannotLeakIntoGoldAndSilver() {
        val model = FriendshipViewModel()
        model.onAction(FriendshipAction.Rules(FriendshipRules.CRYSTAL))
        model.onAction(FriendshipAction.Event(FriendshipEvent.LEVEL_AT_CAPTURE_PLACE))
        assertEquals(FriendshipEvent.LEVEL_AT_CAPTURE_PLACE, model.state.value.event)
        model.onAction(FriendshipAction.Rules(FriendshipRules.GOLD_SILVER))
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

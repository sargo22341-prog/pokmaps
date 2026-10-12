package org.opensources.pokmaps.ui.guide

import androidx.compose.foundation.layout.Column
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextReplacement
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.domain.guide.BreedingItem
import org.opensources.pokmaps.domain.guide.FriendshipRules
import org.opensources.pokmaps.domain.guide.ParentSex
import org.opensources.pokmaps.domain.guide.ParentValues
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class GbaGuideToolsTest {
    @get:Rule val compose = createComposeRule()

    @Test
    fun parentAcceptsIvThirtyOneAndEverstoneButRejectsThirtyTwo() {
        var values by mutableStateOf(ParentValues(ParentSex.FEMALE))
        compose.setContent {
            Column {
                GbaParentValues(listOf(ParentSex.FEMALE), values, true) { action ->
                    values = (action as BreedingAction.Values).values
                }
            }
        }
        compose.onNode(hasText("IV PV (0–31)")).performTextReplacement("31")
        assertEquals(31, values.ivs[0])
        compose.onNode(hasText("IV PV (0–31)")).performTextReplacement("32")
        assertEquals(31, values.ivs[0])
        compose.onNode(hasText("Objet tenu : Aucun")).performClick()
        compose.onNode(hasText("Pierre Stase")).performClick()
        assertEquals(BreedingItem.EVERSTONE, values.item)
    }

    @Test
    fun gbaFriendshipCheckboxChangesTheCalculatedGain() {
        val model = FriendshipViewModel()
        model.onAction(FriendshipAction.Rules(FriendshipRules.EMERALD))
        var state by mutableStateOf(model.state.value)
        compose.setContent {
            Column {
                GbaFriendshipOptions(state) { action ->
                    model.onAction(action)
                    state = model.state.value
                }
            }
        }
        // La case entière est accessible au lecteur d'écran, y compris son libellé.
        compose.onNode(hasText("Grelot Zen")).performClick()
        assertTrue(state.sootheBell)
        assertEquals(77, state.result)
    }
}

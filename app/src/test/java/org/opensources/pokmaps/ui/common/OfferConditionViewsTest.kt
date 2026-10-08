package org.opensources.pokmaps.ui.common

import android.content.Context
import androidx.compose.foundation.layout.Column
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.test.core.app.ApplicationProvider
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.map.NpcOffer
import org.opensources.pokmaps.domain.map.OfferCondition
import org.opensources.pokmaps.domain.map.OfferItem
import org.opensources.pokmaps.domain.map.Weekday
import org.opensources.pokmaps.domain.model.EncounterTime
import org.opensources.pokmaps.domain.model.SpritePlace
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class OfferConditionViewsTest {
    @get:Rule
    val compose = createComposeRule()

    private val context: Context = ApplicationProvider.getApplicationContext()
    private val potion = OfferItem(17, "potion", "Potion", hasSprite = false)
    private val berry = OfferItem(132, "oran-berry", "Baie Oran", hasSprite = false)

    @Test
    fun conditionSharedByAllOffersIsShownOnce() {
        val afterParcel = OfferCondition(story = listOf("Après avoir remis le colis au Prof. Chen"))
        val offers = listOf(NpcOffer.Sale(potion, 300, afterParcel), NpcOffer.Sale(berry, 20, afterParcel))
        compose.setContent { Column { Offers(offers, SpritePlace.MAP) } }
        compose.onNode(hasText(context.getString(R.string.map_offer_conditions))).assertExists()
        compose.onAllNodes(hasText("Après avoir remis le colis au Prof. Chen")).assertCountEquals(1)
    }

    @Test
    fun conditionOfOneOfferIsShownUnderIt() {
        val mondayNight = OfferCondition(
            times = setOf(EncounterTime.NIGHT),
            weekdays = setOf(Weekday.MONDAY, Weekday.SATURDAY, Weekday.WEDNESDAY),
            story = listOf("Après le badge Zéphyr")
        )
        val offers = listOf(NpcOffer.GiftItem(berry, 1, mondayNight), NpcOffer.GiftItem(potion, 1))
        compose.setContent { Column { Offers(offers, SpritePlace.MAP) } }
        compose.onNode(hasText(context.getString(R.string.map_offer_conditions))).assertDoesNotExist()
        // Jours dans l'ordre de la semaine, puis moments.
        compose.onNode(hasText("Le lundi, le mercredi et le samedi, la nuit")).assertExists()
        compose.onNode(hasText("Après le badge Zéphyr")).assertExists()
    }

    @Test
    fun offersWithoutConditionShowNothingMore() {
        compose.setContent { Column { OfferConditionLines(OfferCondition.ALWAYS) } }
        compose.onNode(hasText("Après", substring = true)).assertDoesNotExist()
    }
}

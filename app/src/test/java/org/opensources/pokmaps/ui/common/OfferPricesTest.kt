package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.layout.Column
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.v2.createComposeRule
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.domain.map.CharacterService
import org.opensources.pokmaps.domain.map.NpcOffer
import org.opensources.pokmaps.domain.map.OfferCurrency
import org.opensources.pokmaps.domain.map.OfferItem
import org.opensources.pokmaps.domain.model.SpritePlace
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class OfferPricesTest {
    @get:Rule
    val compose = createComposeRule()

    private val item = OfferItem(17, "potion", "Potion", false)

    @Test
    fun salesAndTutorsShowTheirActualCurrency() {
        val offers = listOf(
            NpcOffer.Sale(item, 250, currency = OfferCurrency.ASHES),
            NpcOffer.Sale(item, 1, currency = OfferCurrency.BATTLE_POINTS),
            NpcOffer.Service(CharacterService.MOVE_TUTOR, 48, currency = OfferCurrency.BATTLE_POINTS)
        )
        compose.setContent { Column { Offers(offers, SpritePlace.MAP) } }
        compose.onNode(hasText("250 cendres")).assertExists()
        compose.onNode(hasText("1 Point Combat")).assertExists()
        compose.onNode(hasText("48 Points Combat")).assertExists()
        compose.onNode(hasText("Enseigne une capacité à un Pokémon.")).assertExists()
    }

    @Test
    fun existingMoneyCoinsAndBlueCardPointsRemainDistinct() {
        val offers = listOf(
            NpcOffer.Sale(item, 300),
            NpcOffer.Service(CharacterService.MOVE_TUTOR, 4000),
            NpcOffer.PointPrize(item, 2)
        )
        compose.setContent { Column { Offers(offers, SpritePlace.MAP) } }
        compose.onNode(hasText("300 ₽")).assertExists()
        compose.onNode(hasText("4000 jetons")).assertExists()
        compose.onNode(hasText("2 points de la Carte Bleue")).assertExists()
        compose.onNode(hasText("2 Points Combat")).assertDoesNotExist()
    }

    @Test
    fun relearnerShowsTheRequiredItemAndFreeTutorHasNoPrice() {
        val scale = OfferItem(93, "heart-scale", "Écaille Cœur", false)
        val offers = listOf(
            NpcOffer.Service(CharacterService.MOVE_RELEARNER, requiredItem = scale),
            NpcOffer.Service(CharacterService.MOVE_TUTOR)
        )
        compose.setContent { Column { Offers(offers, SpritePlace.MAP) } }
        compose.onNode(hasText("Objet requis : Écaille Cœur")).assertExists()
        compose.onNode(hasText("Réapprend une capacité à un Pokémon.")).assertExists()
        compose.onNode(hasText("Enseigne une capacité à un Pokémon.")).assertExists()
        compose.onNode(hasText("0 ₽")).assertDoesNotExist()
    }
}

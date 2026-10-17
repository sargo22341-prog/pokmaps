package org.opensources.pokmaps.domain.map

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class OfferPaymentsTest {
    private val red = OfferItem(72, "red-shard", "Tesson Rouge", true)
    private val blue = OfferItem(73, "blue-shard", "Tesson Bleu", true)
    private val star = OfferItem(91, "star-piece", "Morceau d’Étoile", true)

    @Test
    fun shardTutorKeepsEachColorAndQuantity() {
        val costs = listOf(OfferItemCost(red, 2), OfferItemCost(blue, 6))
        val tutor = NpcOffer.Service(CharacterService.MOVE_TUTOR, requiredItems = costs)
        assertEquals(costs, tutor.requiredItems)
        assertEquals(null, tutor.price)
        assertThrows(IllegalArgumentException::class.java) { OfferItemCost(red, 0) }
        assertThrows(IllegalArgumentException::class.java) {
            NpcOffer.Service(CharacterService.MOVE_TUTOR, requiredItems = listOf(costs[0], costs[0]))
        }
        assertThrows(IllegalArgumentException::class.java) {
            NpcOffer.Service(CharacterService.MOVE_TUTOR, requiredItem = red, requiredItems = costs)
        }
    }

    @Test
    fun shardBundleHasOnePaymentForAllReceivedItems() {
        val exchange = NpcOffer.Exchange(red, star, extraItems = listOf(OfferItemCost(blue, 1)))
        assertEquals(1, exchange.wantedQuantity)
        assertEquals(listOf(OfferItemCost(blue, 1)), exchange.extraItems)
        val machine = NpcOffer.Exchange(star, red, wantedQuantity = 10)
        assertEquals(10, machine.wantedQuantity)
        assertThrows(IllegalArgumentException::class.java) { NpcOffer.Exchange(red, star, wantedQuantity = 0) }
        assertThrows(IllegalArgumentException::class.java) {
            NpcOffer.Exchange(red, star, extraItems = listOf(OfferItemCost(red, 1)))
        }
    }

    @Test
    fun sinnohServicesKeepTheirKindsRolesAndCurrency() {
        val shop = NpcOffer.Service(CharacterService.ACCESSORY_SHOP)
        val cards = NpcOffer.Service(CharacterService.SCRATCH_CARDS, 1, currency = OfferCurrency.BATTLE_POINTS)
        assertEquals(OfferKind.ACCESSORY_SHOP, shop.kind)
        assertEquals(OfferKind.SCRATCH_CARDS, cards.kind)
        assertEquals(OfferCurrency.BATTLE_POINTS, cards.currency)
        assertEquals(
            listOf(CharacterRole.CHARACTER, CharacterRole.SHOP, CharacterRole.PRIZES),
            CharacterRole.of(MapObjectKind.NPC, listOf(shop.kind, cards.kind))
        )
    }
}

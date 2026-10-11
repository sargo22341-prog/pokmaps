package org.opensources.pokmaps.domain.map

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class OfferCurrencyTest {
    @Test
    fun currenciesMatchThePreparedCatalog() {
        assertEquals(OfferCurrency.entries, OfferCurrency.entries.map { OfferCurrency.from(it.identifier) })
        assertThrows(IllegalArgumentException::class.java) { OfferCurrency.from("points") }
    }

    @Test
    fun existingPricesKeepTheirCurrency() {
        val item = OfferItem(17, "potion", "Potion", false)
        assertEquals(OfferCurrency.MONEY, NpcOffer.Sale(item, 300).currency)
        assertEquals(OfferCurrency.COINS, NpcOffer.Service(CharacterService.MOVE_TUTOR, 4000).currency)
        assertEquals(OfferCurrency.MONEY, NpcOffer.Service(CharacterService.GROOMING, 500).currency)
    }

    @Test
    fun hoennServicesHaveExplicitKindsAndRoles() {
        val services = mapOf(
            CharacterService.DAYCARE_EGG to OfferKind.DAYCARE_EGG,
            CharacterService.DAYCARE_WITHDRAWAL to OfferKind.DAYCARE_WITHDRAWAL,
            CharacterService.MOVE_RELEARNER to OfferKind.MOVE_RELEARNER
        )
        services.forEach { (service, kind) -> assertEquals(kind, NpcOffer.Service(service).kind) }
        assertEquals(
            listOf(CharacterRole.CHARACTER, CharacterRole.DAYCARE, CharacterRole.MOVE_RELEARNER),
            CharacterRole.of(MapObjectKind.NPC, services.values)
        )
    }
}

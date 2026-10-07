package org.opensources.pokmaps.domain.map

import org.junit.Assert.assertEquals
import org.junit.Test

/** Icônes d'un élément de la carte : ce qu'il est, puis ce qu'on peut y faire, dans un ordre fixe. */
class CharacterRoleTest {
    @Test
    fun aTrainerIsABattle() {
        assertEquals(listOf(CharacterRole.BATTLE), CharacterRole.of(MapObjectKind.TRAINER, emptyList()))
    }

    @Test
    fun aCharacterShowsWhatItDoes() {
        val offers = listOf(OfferKind.SALE, OfferKind.HEAL, OfferKind.SALE, OfferKind.EXCHANGE, OfferKind.GIFT_ITEM)
        assertEquals(
            listOf(
                CharacterRole.CHARACTER,
                CharacterRole.HEAL,
                CharacterRole.SHOP,
                CharacterRole.GIFT,
                CharacterRole.TRADE
            ),
            CharacterRole.of(MapObjectKind.NPC, offers)
        )
    }

    @Test
    fun aFacilityIsOnlyItsFunction() {
        assertEquals(
            listOf(CharacterRole.PRIZES),
            CharacterRole.of(MapObjectKind.PRIZE_VENDOR, listOf(OfferKind.PRIZE_POKEMON, OfferKind.PRIZE_ITEM))
        )
        assertEquals(
            listOf(CharacterRole.SHOP),
            CharacterRole.of(MapObjectKind.VENDING_MACHINE, listOf(OfferKind.SALE))
        )
    }

    @Test
    fun objectsAndPokemonAreNotPeople() {
        assertEquals(
            listOf(CharacterRole.OBJECT, CharacterRole.GIFT),
            CharacterRole.of(MapObjectKind.NPC_OBJECT, listOf(OfferKind.GIFT_ITEM))
        )
        assertEquals(listOf(CharacterRole.POKEMON), CharacterRole.of(MapObjectKind.NPC_POKEMON, emptyList()))
    }

    @Test
    fun anItemHasNoRole() {
        assertEquals(emptyList<CharacterRole>(), CharacterRole.of(MapObjectKind.HIDDEN_ITEM, emptyList()))
    }

    @Test
    fun everyOfferKindHasARole() {
        val roles = CharacterRole.of(MapObjectKind.NPC, OfferKind.entries)
        val identities = setOf(CharacterRole.BATTLE, CharacterRole.OBJECT, CharacterRole.POKEMON)
        assertEquals(CharacterRole.entries - identities, roles)
    }
}

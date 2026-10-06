package org.opensources.pokmaps.domain.map

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

/** Types lus dans la base : une valeur inconnue est une erreur, jamais un repli silencieux. */
class MapKindsTest {
    @Test
    fun knownIdentifiersAreRead() {
        assertEquals(MapObjectKind.entries, MapObjectKind.entries.map { MapObjectKind.from(it.identifier) })
        assertEquals(SpotKind.entries, SpotKind.entries.map { SpotKind.from(it.identifier) })
        assertEquals(OfferKind.entries, OfferKind.entries.map { OfferKind.from(it.identifier) })
    }

    @Test
    fun unknownIdentifiersAreErrors() {
        assertThrows(IllegalArgumentException::class.java) { MapObjectKind.from("sign") }
        assertThrows(IllegalArgumentException::class.java) { SpotKind.from("lava") }
        assertThrows(IllegalArgumentException::class.java) { OfferKind.from("loan") }
    }
}

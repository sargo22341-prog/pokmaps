package org.opensources.pokmaps.domain.guide

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class HgssRoamersTest {
    @Test
    fun cartridgesKeepTheirEonSpeciesAndOnlyTwoBeastsRoamAtTheirNativeLevels() {
        assertEquals(listOf(243, 244, 380), Roamers.pokemonIds(15))
        assertEquals(listOf(243, 244, 381), Roamers.pokemonIds(16))
        for (version in 15..16) {
            Roamers.pokemonIds(version).forEach { pokemon ->
                val eon = pokemon in setOf(380, 381)
                assertEquals(if (eon) 35 else 40, Roamers.level(version, pokemon))
                assertEquals(if (eon) RoamerArea.KANTO else RoamerArea.JOHTO, Roamers.area(version, pokemon))
                assertEquals(if (eon) 25 else 16, RoamerObservations.places(version, pokemon).size)
                assertEquals(
                    if (eon) RoamerCondition.HGSS_EON else RoamerCondition.JOHTO,
                    Roamers.choices(version).single { it.pokemonId == pokemon }.condition
                )
            }
        }
        assertThrows(IllegalArgumentException::class.java) {
            RoamerObservations.validate(15, mapOf(245 to "route-29"))
        }
        assertThrows(IllegalArgumentException::class.java) {
            RoamerObservations.validate(15, mapOf(380 to "route-23"))
        }
    }
}

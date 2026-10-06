package org.opensources.pokmaps.domain.pokemon

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class DamageClassTest {
    @Test
    fun knownClassesAreRead() {
        assertEquals(
            listOf(DamageClass.PHYSICAL, DamageClass.SPECIAL, DamageClass.STATUS),
            listOf("physical", "special", "status").map(DamageClass::from)
        )
    }

    /** Avant, toute valeur inattendue devenait « Statut » sans que personne ne le voie. */
    @Test
    fun anUnknownClassIsAnError() {
        assertThrows(IllegalArgumentException::class.java) { DamageClass.from("shadow") }
    }
}

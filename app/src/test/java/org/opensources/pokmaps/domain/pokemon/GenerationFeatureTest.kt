package org.opensources.pokmaps.domain.pokemon

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class GenerationFeatureTest {
    @Test
    fun featuresAppearWithTheirGeneration() {
        assertFalse(GenerationFeature.HELD_ITEMS.existsIn(1))
        assertTrue(GenerationFeature.HELD_ITEMS.existsIn(2))
        assertFalse(GenerationFeature.ABILITIES.existsIn(2))
        assertTrue(GenerationFeature.ABILITIES.existsIn(3))
    }

    @Test
    fun shinyOddsByGeneration() {
        assertNull(ShinyOdds.oneIn(1))
        assertEquals(8192, ShinyOdds.oneIn(2))
        assertEquals(8192, ShinyOdds.oneIn(5))
        assertEquals(4096, ShinyOdds.oneIn(6))
    }

    @Test
    fun genderRatioFromPokeApiRate() {
        assertEquals(GenderRatio.Genderless, GenderRatio.from(-1))
        val bulbasaur = GenderRatio.from(1) as GenderRatio.Gendered
        assertEquals(87.5, bulbasaur.malePercent, 0.0)
        assertEquals(12.5, bulbasaur.femalePercent, 0.0)
        assertEquals(100.0, (GenderRatio.from(8) as GenderRatio.Gendered).femalePercent, 0.0)
    }

    @Test(expected = IllegalArgumentException::class)
    fun anInvalidRateIsRejected() {
        GenderRatio.from(9)
    }
}

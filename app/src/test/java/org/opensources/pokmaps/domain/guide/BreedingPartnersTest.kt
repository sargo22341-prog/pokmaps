package org.opensources.pokmaps.domain.guide

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.opensources.pokmaps.domain.pokemon.GenderRatio

class BreedingPartnersTest {
    private val female = BreedingProfile(1, GenderRatio.Gendered(1), setOf("Monstrueux", "Végétal"))
    private val ditto = BreedingProfile(132, GenderRatio.Genderless, setOf("Métamorph"))

    @Test
    fun partnersShareEitherEggGroupAndAnOppositeSex() {
        val plant = BreedingProfile(43, GenderRatio.Gendered(4), setOf("Végétal"))
        val mineral = BreedingProfile(74, GenderRatio.Gendered(4), setOf("Min?ral"))
        val onlyFemale = BreedingProfile(29, GenderRatio.Gendered(8), setOf("Monstrueux"))
        assertTrue(BreedingPartners.compatible(female, ParentSex.FEMALE, female))
        assertTrue(BreedingPartners.compatible(female, ParentSex.FEMALE, plant))
        assertFalse(BreedingPartners.compatible(female, ParentSex.FEMALE, mineral))
        assertFalse(BreedingPartners.compatible(female, ParentSex.FEMALE, onlyFemale))
        assertTrue(BreedingPartners.compatible(female, ParentSex.MALE, onlyFemale))
    }

    @Test
    fun dittoAcceptsGenderlessAndSingleSexSpeciesButNeitherSterileSpeciesNorDitto() {
        val magnet = BreedingProfile(81, GenderRatio.Genderless, setOf("Min?ral"))
        val male = BreedingProfile(128, GenderRatio.Gendered(0), setOf("Terrestre"))
        val baby = BreedingProfile(172, GenderRatio.Gendered(4), setOf("Inconnu"))
        assertTrue(BreedingPartners.compatible(magnet, ParentSex.GENDERLESS, ditto))
        assertTrue(BreedingPartners.compatible(ditto, ParentSex.GENDERLESS, male))
        assertFalse(BreedingPartners.compatible(magnet, ParentSex.GENDERLESS, magnet))
        assertFalse(BreedingPartners.compatible(ditto, ParentSex.GENDERLESS, baby))
        assertFalse(BreedingPartners.compatible(baby, ParentSex.FEMALE, ditto))
        assertFalse(BreedingPartners.compatible(ditto, ParentSex.GENDERLESS, ditto))
    }

    @Test
    fun defaultPrefersSameSpeciesThenDittoThenAnotherPartnerOrNone() {
        assertEquals(1, BreedingPartners.defaultPartner(1, listOf(43, 132, 1)))
        assertEquals(132, BreedingPartners.defaultPartner(128, listOf(1, 132)))
        assertEquals(43, BreedingPartners.defaultPartner(29, listOf(43)))
        assertEquals(null, BreedingPartners.defaultPartner(172, emptyList()))
    }
}

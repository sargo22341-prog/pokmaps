package org.opensources.pokmaps.domain.guide

import org.opensources.pokmaps.domain.pokemon.GenderRatio

data class BreedingProfile(val id: Int, val gender: GenderRatio, val groups: Set<String>) {
    val fertile: Boolean = groups.isNotEmpty() && "Inconnu" !in groups
    val sexes: List<ParentSex> = when (val ratio = gender) {
        GenderRatio.Genderless -> listOf(ParentSex.GENDERLESS)

        is GenderRatio.Gendered -> buildList {
            if (ratio.femaleEighths < 8) add(ParentSex.MALE)
            if (ratio.femaleEighths > 0) add(ParentSex.FEMALE)
        }
    }
}

object BreedingPartners {
    fun compatible(first: BreedingProfile, sex: ParentSex, second: BreedingProfile): Boolean {
        if (!first.fertile || !second.fertile) return false
        if (first.id == BreedingRules.DITTO && second.id == BreedingRules.DITTO) return false
        if (first.id == BreedingRules.DITTO || second.id == BreedingRules.DITTO) return true
        return sex != ParentSex.GENDERLESS && opposite(sex) in second.sexes &&
            first.groups.any { it in second.groups }
    }

    fun opposite(sex: ParentSex): ParentSex = when (sex) {
        ParentSex.MALE -> ParentSex.FEMALE
        ParentSex.FEMALE -> ParentSex.MALE
        ParentSex.GENDERLESS -> ParentSex.GENDERLESS
    }

    fun defaultPartner(firstId: Int, ids: List<Int>): Int? =
        ids.firstOrNull { it == firstId } ?: ids.firstOrNull { it == BreedingRules.DITTO } ?: ids.firstOrNull()
}

package org.opensources.pokmaps.data.guide

import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.Gen3CaptureGoals
import org.opensources.pokmaps.domain.guide.GuideCategory

internal fun gbaCollectionGuides(version: Int): List<GuideDefinition> {
    require(version in 7..11) { "Version GBA inconnue : $version" }
    val hoenn = version <= 9
    val prefix = if (hoenn) "hoenn" else "remake"
    val source = when (version) {
        7, 8 -> "https://github.com/pret/pokeruby/tree/5784633ce4ef/src/data/pokemon"
        9 -> "https://github.com/pret/pokeemerald/tree/731ad5bfd6e6/src/data/pokemon"
        10, 11 -> "https://github.com/pret/pokefirered/tree/037335f4c725/src/data/pokemon"
        else -> error("Version GBA inconnue : $version")
    }
    return listOf(
        GuideDefinition(
            "$prefix-regional-collection",
            R.string.guide_gba_regional_title,
            if (hoenn) R.string.guide_hoenn_collection_text else R.string.guide_remake_collection_text,
            GuideCategory.SIDE_QUEST,
            setOf(version),
            if (hoenn) 252 else 1,
            listOf(source),
            captureGoal = Gen3CaptureGoals.forVersion(version, regional = true)
        ),
        GuideDefinition(
            "$prefix-national-collection",
            R.string.guide_gba_national_title,
            if (hoenn) R.string.guide_hoenn_national_text else R.string.guide_remake_collection_text,
            GuideCategory.SIDE_QUEST,
            setOf(version),
            if (hoenn) 252 else 1,
            listOf(source),
            captureGoal = Gen3CaptureGoals.forVersion(version)
        )
    )
}

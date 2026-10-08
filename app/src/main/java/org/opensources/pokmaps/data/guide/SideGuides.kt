package org.opensources.pokmaps.data.guide

import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.GuideCategory

internal fun sideGuides(): List<GuideDefinition> = DEFINITIONS

private val DEFINITIONS = listOf(
    GuideDefinition(
        "johto-alph",
        R.string.guide_alph_title,
        R.string.guide_alph_text,
        GuideCategory.SIDE_QUEST,
        JOHTO_VERSIONS,
        201,
        listOf("https://github.com/pret/pokecrystal")
    ),
    GuideDefinition(
        "johto-gifts",
        R.string.guide_gifts_title,
        R.string.guide_gifts_text,
        GuideCategory.SIDE_QUEST,
        JOHTO_VERSIONS,
        175,
        listOf(JOHTO_SOURCE)
    ),
    GuideDefinition(
        "kanto-dojo",
        R.string.guide_dojo_title,
        R.string.guide_dojo_text,
        GuideCategory.SIDE_QUEST,
        KANTO_VERSIONS,
        106,
        listOf(KANTO_SOURCE)
    ),
    GuideDefinition(
        "kanto-fossils",
        R.string.guide_fossils_title,
        R.string.guide_fossils_text,
        GuideCategory.SIDE_QUEST,
        KANTO_VERSIONS,
        142,
        listOf(KANTO_SOURCE)
    )
)

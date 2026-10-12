package org.opensources.pokmaps.data.guide

import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.GuideCategory

internal fun gbaToolGuides(): List<GuideDefinition> = listOf(
    GuideDefinition(
        "breeding",
        R.string.guide_breeding_title,
        R.string.guide_breeding_gba_text,
        GuideCategory.TIP,
        RUBY_SAPPHIRE_VERSIONS + EMERALD_VERSIONS + FIRERED_LEAFGREEN_VERSIONS,
        183,
        SOURCES.map { "$it/src/daycare.c" }
    ),
    GuideDefinition(
        "friendship",
        R.string.guide_friendship_title,
        R.string.guide_friendship_gba_text,
        GuideCategory.TIP,
        RUBY_SAPPHIRE_VERSIONS + EMERALD_VERSIONS + FIRERED_LEAFGREEN_VERSIONS,
        172,
        listOf(
            "${SOURCES[0]}/src/pokemon_3.c",
            "${SOURCES[1]}/src/pokemon.c",
            "${SOURCES[2]}/src/pokemon.c"
        )
    )
)

private val SOURCES = listOf(
    "https://github.com/pret/pokeruby/blob/5784633ce4ef",
    "https://github.com/pret/pokeemerald/blob/731ad5bfd6e6",
    "https://github.com/pret/pokefirered/blob/037335f4c725"
)

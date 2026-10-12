package org.opensources.pokmaps.data.guide

import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.GuideCategory

internal fun hoennCalendarGuides(): List<GuideDefinition> = DEFINITIONS

private val VERSIONS = RUBY_SAPPHIRE_VERSIONS + EMERALD_VERSIONS
private val SOURCES = listOf(
    "https://github.com/pret/pokeruby/blob/5784633ce4ef/src/time_events.c",
    "https://github.com/pret/pokeemerald/blob/731ad5bfd6e6/src/time_events.c",
    "https://github.com/pret/pokeemerald/blob/731ad5bfd6e6/src/clock.c",
    "https://github.com/pret/pokeemerald/blob/731ad5bfd6e6/src/lottery_corner.c"
)

private val DEFINITIONS = listOf(
    GuideDefinition(
        "hoenn-mirage",
        R.string.guide_hoenn_mirage_title,
        R.string.guide_hoenn_mirage_text,
        GuideCategory.CALENDAR,
        VERSIONS,
        360,
        SOURCES
    ),
    GuideDefinition(
        "hoenn-tides",
        R.string.guide_hoenn_tides_title,
        R.string.guide_hoenn_tides_text,
        GuideCategory.CALENDAR,
        VERSIONS,
        363,
        SOURCES
    ),
    GuideDefinition(
        "hoenn-lottery",
        R.string.guide_hoenn_lottery_title,
        R.string.guide_hoenn_lottery_text,
        GuideCategory.CALENDAR,
        VERSIONS,
        263,
        SOURCES
    ),
    GuideDefinition(
        "hoenn-clock",
        R.string.guide_hoenn_clock_title,
        R.string.guide_hoenn_clock_text,
        GuideCategory.CALENDAR,
        VERSIONS,
        315,
        SOURCES
    ),
    GuideDefinition(
        "hoenn-trick-house",
        R.string.guide_hoenn_trick_house_title,
        R.string.guide_hoenn_trick_house_text,
        GuideCategory.SIDE_QUEST,
        VERSIONS,
        327,
        listOf(
            "https://github.com/pret/pokeruby/blob/5784633ce4ef/data/maps/Route110_TrickHouseEntrance/scripts.inc",
            "https://github.com/pret/pokeemerald/blob/731ad5bfd6e6/data/maps/Route110_TrickHouseEntrance/scripts.inc"
        )
    )
)

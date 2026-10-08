package org.opensources.pokmaps.data.guide

import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.GuideCategory

internal fun tipGuides(): List<GuideDefinition> = DEFINITIONS

private val DEFINITIONS = listOf(
    GuideDefinition(
        "breeding",
        R.string.guide_breeding_title,
        R.string.guide_breeding_text,
        GuideCategory.TIP,
        JOHTO_VERSIONS,
        132,
        listOf("https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_breeding")
    ),
    GuideDefinition(
        "friendship",
        R.string.guide_friendship_title,
        R.string.guide_friendship_text,
        GuideCategory.TIP,
        JOHTO_VERSIONS,
        175,
        listOf("https://bulbapedia.bulbagarden.net/wiki/Friendship")
    ),
    GuideDefinition(
        "yellow-gifts",
        R.string.guide_yellow_gifts_title,
        R.string.guide_yellow_gifts_text,
        GuideCategory.TIP,
        setOf(3),
        1,
        listOf("https://www.eternia.fr/dossier/pokemon-version-jaune")
    ),
    GuideDefinition(
        "kanto-preparation",
        R.string.guide_kanto_preparation_title,
        R.string.guide_kanto_preparation_text,
        GuideCategory.TIP,
        KANTO_VERSIONS,
        63,
        listOf("https://github.com/pret/pokered")
    ),
    GuideDefinition(
        "johto-balls",
        R.string.guide_johto_balls_title,
        R.string.guide_johto_balls_text,
        GuideCategory.TIP,
        JOHTO_VERSIONS,
        214,
        listOf("https://github.com/pret/pokecrystal")
    ),
    GuideDefinition(
        "mew-glitch",
        R.string.guide_mew_glitch_title,
        R.string.guide_mew_glitch_text,
        GuideCategory.GLITCH,
        KANTO_VERSIONS,
        151,
        listOf("https://www.pokemontrash.com/rouge-bleu-jaune/avoir-mew")
    ),
    GuideDefinition(
        "cinnabar-glitch",
        R.string.guide_cinnabar_glitch_title,
        R.string.guide_cinnabar_glitch_text,
        GuideCategory.GLITCH,
        setOf(1, 2),
        150,
        listOf("https://bulbapedia.bulbagarden.net/wiki/Old_man_glitch")
    ),
    GuideDefinition(
        "clone-gen2",
        R.string.guide_clone_gen2_title,
        R.string.guide_clone_gen2_text,
        GuideCategory.GLITCH,
        JOHTO_VERSIONS,
        132,
        listOf("https://bulbapedia.bulbagarden.net/wiki/Cloning_glitches")
    ),
    GuideDefinition(
        "glitch-combat",
        R.string.guide_glitch_combat_title,
        R.string.guide_glitch_combat_text,
        GuideCategory.GLITCH,
        KANTO_VERSIONS,
        93,
        listOf("https://github.com/pret/pokered")
    ),
    GuideDefinition(
        "day-monday",
        R.string.guide_day_monday_title,
        R.string.guide_day_monday_text,
        GuideCategory.CALENDAR,
        JOHTO_VERSIONS,
        35,
        listOf("https://github.com/pret/pokecrystal", "https://bulbapedia.bulbagarden.net/wiki/Week_Siblings")
    ),
    GuideDefinition(
        "day-tuesday",
        R.string.guide_day_tuesday_title,
        R.string.guide_day_tuesday_text,
        GuideCategory.CALENDAR,
        JOHTO_VERSIONS,
        123,
        listOf("https://github.com/pret/pokecrystal", "https://bulbapedia.bulbagarden.net/wiki/Week_Siblings")
    ),
    GuideDefinition(
        "day-wednesday",
        R.string.guide_day_wednesday_title,
        R.string.guide_day_wednesday_text,
        GuideCategory.CALENDAR,
        JOHTO_VERSIONS,
        130,
        listOf("https://github.com/pret/pokecrystal", "https://bulbapedia.bulbagarden.net/wiki/Week_Siblings")
    ),
    GuideDefinition(
        "day-thursday",
        R.string.guide_day_thursday_title,
        R.string.guide_day_thursday_text,
        GuideCategory.CALENDAR,
        JOHTO_VERSIONS,
        127,
        listOf("https://github.com/pret/pokecrystal", "https://bulbapedia.bulbagarden.net/wiki/Week_Siblings")
    ),
    GuideDefinition(
        "day-friday",
        R.string.guide_day_friday_title,
        R.string.guide_day_friday_text,
        GuideCategory.CALENDAR,
        JOHTO_VERSIONS,
        131,
        listOf("https://github.com/pret/pokecrystal", "https://bulbapedia.bulbagarden.net/wiki/Week_Siblings")
    ),
    GuideDefinition(
        "day-saturday",
        R.string.guide_day_saturday_title,
        R.string.guide_day_saturday_text,
        GuideCategory.CALENDAR,
        JOHTO_VERSIONS,
        12,
        listOf("https://github.com/pret/pokecrystal", "https://bulbapedia.bulbagarden.net/wiki/Week_Siblings")
    ),
    GuideDefinition(
        "day-sunday",
        R.string.guide_day_sunday_title,
        R.string.guide_day_sunday_text,
        GuideCategory.CALENDAR,
        JOHTO_VERSIONS,
        133,
        listOf("https://github.com/pret/pokecrystal", "https://bulbapedia.bulbagarden.net/wiki/Week_Siblings")
    ),
    GuideDefinition(
        "crystal-buena",
        R.string.guide_crystal_buena_title,
        R.string.guide_crystal_buena_text,
        GuideCategory.TIP,
        setOf(6),
        172,
        listOf("https://github.com/pret/pokecrystal")
    )
)

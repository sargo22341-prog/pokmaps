package org.opensources.pokmaps.data.guide

import org.opensources.pokmaps.R

internal fun rubyAchievements(): List<AchievementDefinition> = DEFINITIONS

// Le Pokédex de la collection complète se termine après la Ligue.
private const val COLLECTION_CHAPTER = "hoenn-postgame"

private val DEFINITIONS = listOf(
    AchievementDefinition(31199, 7, R.string.ra_31199_title, R.string.ra_31199_text, 1, false, "hoenn-start"),
    AchievementDefinition(31200, 7, R.string.ra_31200_title, R.string.ra_31200_text, 5, false, "hoenn-mauville"),
    AchievementDefinition(31201, 7, R.string.ra_31201_title, R.string.ra_31201_text, 5, false, "hoenn-fortree"),
    AchievementDefinition(31202, 7, R.string.ra_31202_title, R.string.ra_31202_text, 5, false, "hoenn-hideouts"),
    AchievementDefinition(31205, 7, R.string.ra_31205_title, R.string.ra_31205_text, 5, true, "hoenn-hideouts"),
    AchievementDefinition(31206, 7, R.string.ra_31206_title, R.string.ra_31206_text, 10, false, "hoenn-optional"),
    AchievementDefinition(31207, 7, R.string.ra_31207_title, R.string.ra_31207_text, 10, false, "hoenn-optional"),
    AchievementDefinition(31208, 7, R.string.ra_31208_title, R.string.ra_31208_text, 10, false, "hoenn-optional"),
    AchievementDefinition(31209, 7, R.string.ra_31209_title, R.string.ra_31209_text, 10, false, "hoenn-optional"),
    AchievementDefinition(31210, 7, R.string.ra_31210_title, R.string.ra_31210_text, 10, false, "hoenn-optional"),
    AchievementDefinition(31211, 7, R.string.ra_31211_title, R.string.ra_31211_text, 10, false, "hoenn-optional"),
    AchievementDefinition(31212, 7, R.string.ra_31212_title, R.string.ra_31212_text, 10, false, "hoenn-optional"),
    AchievementDefinition(31213, 7, R.string.ra_31213_title, R.string.ra_31213_text, 10, false, "hoenn-optional"),
    AchievementDefinition(31214, 7, R.string.ra_31214_title, R.string.ra_31214_text, 5, false, "hoenn-volcano"),
    AchievementDefinition(31215, 7, R.string.ra_31215_title, R.string.ra_31215_text, 5, false, "hoenn-fortree"),
    AchievementDefinition(31216, 7, R.string.ra_31216_title, R.string.ra_31216_text, 5, false, "hoenn-hideouts"),
    AchievementDefinition(31217, 7, R.string.ra_31217_title, R.string.ra_31217_text, 5, false, "hoenn-sootopolis"),
    AchievementDefinition(31218, 7, R.string.ra_31218_title, R.string.ra_31218_text, 5, false, "hoenn-league"),
    AchievementDefinition(31223, 7, R.string.ra_31223_title, R.string.ra_31223_text, 25, false, "hoenn-league"),
    AchievementDefinition(31224, 7, R.string.ra_31224_title, R.string.ra_31224_text, 10, true, "hoenn-sootopolis"),
    AchievementDefinition(31225, 7, R.string.ra_31225_title, R.string.ra_31225_text, 10, true, "hoenn-sootopolis"),
    AchievementDefinition(31226, 7, R.string.ra_31226_title, R.string.ra_31226_text, 5, true, "hoenn-regis"),
    AchievementDefinition(31227, 7, R.string.ra_31227_title, R.string.ra_31227_text, 5, true, "hoenn-regis"),
    AchievementDefinition(31228, 7, R.string.ra_31228_title, R.string.ra_31228_text, 5, true, "hoenn-regis"),
    AchievementDefinition(31229, 7, R.string.ra_31229_title, R.string.ra_31229_text, 10, true, "hoenn-postgame"),
    AchievementDefinition(91983, 7, R.string.ra_91983_title, R.string.ra_91983_text, 5, false, "hoenn-mauville"),
    AchievementDefinition(91984, 7, R.string.ra_91984_title, R.string.ra_91984_text, 10, false, "hoenn-optional"),
    AchievementDefinition(91985, 7, R.string.ra_91985_title, R.string.ra_91985_text, 5, false, "hoenn-mossdeep"),
    AchievementDefinition(91986, 7, R.string.ra_91986_title, R.string.ra_91986_text, 5, false, "hoenn-optional"),
    AchievementDefinition(91987, 7, R.string.ra_91987_title, R.string.ra_91987_text, 3, false, "hoenn-hideouts"),
    AchievementDefinition(91988, 7, R.string.ra_91988_title, R.string.ra_91988_text, 5, false, "hoenn-optional"),
    AchievementDefinition(91989, 7, R.string.ra_91989_title, R.string.ra_91989_text, 5, false, "hoenn-optional"),
    AchievementDefinition(91990, 7, R.string.ra_91990_title, R.string.ra_91990_text, 5, false, "hoenn-optional"),
    AchievementDefinition(89506, 7, R.string.ra_89506_title, R.string.ra_89506_text, 10, false, "hoenn-optional"),
    AchievementDefinition(92002, 7, R.string.ra_92002_title, R.string.ra_92002_text, 5, false, "hoenn-optional"),
    AchievementDefinition(92005, 7, R.string.ra_92005_title, R.string.ra_92005_text, 5, true, "hoenn-optional"),
    AchievementDefinition(91997, 7, R.string.ra_91997_title, R.string.ra_91997_text, 5, false, "hoenn-optional"),
    AchievementDefinition(91995, 7, R.string.ra_91995_title, R.string.ra_91995_text, 5, false, "hoenn-optional"),
    AchievementDefinition(92001, 7, R.string.ra_92001_title, R.string.ra_92001_text, 5, false, "hoenn-optional"),
    AchievementDefinition(91996, 7, R.string.ra_91996_title, R.string.ra_91996_text, 1, false, "hoenn-optional"),
    AchievementDefinition(91991, 7, R.string.ra_91991_title, R.string.ra_91991_text, 10, false, "hoenn-optional"),
    AchievementDefinition(92004, 7, R.string.ra_92004_title, R.string.ra_92004_text, 5, false, "hoenn-postgame"),
    AchievementDefinition(92000, 7, R.string.ra_92000_title, R.string.ra_92000_text, 10, false, "hoenn-league"),
    AchievementDefinition(91992, 7, R.string.ra_91992_title, R.string.ra_91992_text, 25, false, "hoenn-postgame"),
    AchievementDefinition(91993, 7, R.string.ra_91993_title, R.string.ra_91993_text, 25, false, "hoenn-postgame"),
    AchievementDefinition(91994, 7, R.string.ra_91994_title, R.string.ra_91994_text, 50, false, "hoenn-postgame"),
    AchievementDefinition(91999, 7, R.string.ra_91999_title, R.string.ra_91999_text, 10, false, "hoenn-fortree"),
    AchievementDefinition(92003, 7, R.string.ra_92003_title, R.string.ra_92003_text, 25, true, "hoenn-postgame"),
    AchievementDefinition(91998, 7, R.string.ra_91998_title, R.string.ra_91998_text, 50, true, COLLECTION_CHAPTER)
)

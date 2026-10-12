package org.opensources.pokmaps.data.guide

import org.opensources.pokmaps.R

internal fun fireRedAchievements(): List<AchievementDefinition> = DEFINITIONS

private const val ZARBI_CHAPTER = "remake-collections"

private const val COLLECTION_CHAPTER = "remake-national-collection"

private const val PREP_CHAPTER = "remake-preparation"

private val DEFINITIONS = listOf(
    AchievementDefinition(33592, 10, R.string.ra_33592_title, R.string.ra_33592_text, 1, true, "remake-start"),
    AchievementDefinition(33593, 10, R.string.ra_33593_title, R.string.ra_33593_text, 5, true, "remake-brock"),
    AchievementDefinition(33601, 10, R.string.ra_33601_title, R.string.ra_33601_text, 5, false, "remake-brock"),
    AchievementDefinition(195143, 10, R.string.ra_195143_title, R.string.ra_195143_text, 10, true, "remake-brock"),
    AchievementDefinition(33594, 10, R.string.ra_33594_title, R.string.ra_33594_text, 5, false, "remake-misty"),
    AchievementDefinition(33602, 10, R.string.ra_33602_title, R.string.ra_33602_text, 5, false, "remake-misty"),
    AchievementDefinition(195146, 10, R.string.ra_195146_title, R.string.ra_195146_text, 10, true, "remake-misty"),
    AchievementDefinition(33595, 10, R.string.ra_33595_title, R.string.ra_33595_text, 5, false, "remake-ship"),
    AchievementDefinition(33603, 10, R.string.ra_33603_title, R.string.ra_33603_text, 5, false, "remake-ship"),
    AchievementDefinition(195147, 10, R.string.ra_195147_title, R.string.ra_195147_text, 10, true, "remake-ship"),
    AchievementDefinition(33596, 10, R.string.ra_33596_title, R.string.ra_33596_text, 5, false, "remake-flute"),
    AchievementDefinition(33604, 10, R.string.ra_33604_title, R.string.ra_33604_text, 5, false, "remake-celadon"),
    AchievementDefinition(195153, 10, R.string.ra_195153_title, R.string.ra_195153_text, 10, true, "remake-celadon"),
    AchievementDefinition(33599, 10, R.string.ra_33599_title, R.string.ra_33599_text, 5, false, "remake-celadon"),
    AchievementDefinition(33605, 10, R.string.ra_33605_title, R.string.ra_33605_text, 5, false, "remake-flute"),
    AchievementDefinition(195157, 10, R.string.ra_195157_title, R.string.ra_195157_text, 10, true, "remake-flute"),
    AchievementDefinition(33597, 10, R.string.ra_33597_title, R.string.ra_33597_text, 5, false, "remake-saffron"),
    AchievementDefinition(33600, 10, R.string.ra_33600_title, R.string.ra_33600_text, 10, false, "remake-saffron"),
    AchievementDefinition(33606, 10, R.string.ra_33606_title, R.string.ra_33606_text, 5, false, "remake-saffron"),
    AchievementDefinition(195159, 10, R.string.ra_195159_title, R.string.ra_195159_text, 10, true, "remake-saffron"),
    AchievementDefinition(33607, 10, R.string.ra_33607_title, R.string.ra_33607_text, 5, false, "remake-cinnabar"),
    AchievementDefinition(195160, 10, R.string.ra_195160_title, R.string.ra_195160_text, 10, true, "remake-cinnabar"),
    AchievementDefinition(33626, 10, R.string.ra_33626_title, R.string.ra_33626_text, 5, false, "remake-sevii"),
    AchievementDefinition(33608, 10, R.string.ra_33608_title, R.string.ra_33608_text, 5, false, "remake-league"),
    AchievementDefinition(195161, 10, R.string.ra_195161_title, R.string.ra_195161_text, 10, true, "remake-league"),
    AchievementDefinition(33598, 10, R.string.ra_33598_title, R.string.ra_33598_text, 5, false, "remake-league"),
    AchievementDefinition(33613, 10, R.string.ra_33613_title, R.string.ra_33613_text, 25, false, "remake-league"),
    AchievementDefinition(195162, 10, R.string.ra_195162_title, R.string.ra_195162_text, 25, true, "remake-league"),
    AchievementDefinition(33627, 10, R.string.ra_33627_title, R.string.ra_33627_text, 5, false, "remake-ruby"),
    AchievementDefinition(33628, 10, R.string.ra_33628_title, R.string.ra_33628_text, 5, false, "remake-sapphire"),
    AchievementDefinition(33629, 10, R.string.ra_33629_title, R.string.ra_33629_text, 5, false, PREP_CHAPTER),
    AchievementDefinition(33618, 10, R.string.ra_33618_title, R.string.ra_33618_text, 25, false, "remake-league"),
    AchievementDefinition(195166, 10, R.string.ra_195166_title, R.string.ra_195166_text, 25, false, "remake-league"),
    AchievementDefinition(33623, 10, R.string.ra_33623_title, R.string.ra_33623_text, 10, true, "remake-legends"),
    AchievementDefinition(33630, 10, R.string.ra_33630_title, R.string.ra_33630_text, 5, false, "remake-sapphire"),
    AchievementDefinition(33631, 10, R.string.ra_33631_title, R.string.ra_33631_text, 5, false, "remake-sapphire"),
    AchievementDefinition(33632, 10, R.string.ra_33632_title, R.string.ra_33632_text, 5, false, "remake-sapphire"),
    AchievementDefinition(33633, 10, R.string.ra_33633_title, R.string.ra_33633_text, 5, false, "remake-sapphire"),
    AchievementDefinition(33619, 10, R.string.ra_33619_title, R.string.ra_33619_text, 5, false, ZARBI_CHAPTER),
    AchievementDefinition(33622, 10, R.string.ra_33622_title, R.string.ra_33622_text, 5, true, "remake-legends"),
    AchievementDefinition(33621, 10, R.string.ra_33621_title, R.string.ra_33621_text, 5, true, "remake-legends"),
    AchievementDefinition(33620, 10, R.string.ra_33620_title, R.string.ra_33620_text, 5, true, "remake-legends"),
    AchievementDefinition(33624, 10, R.string.ra_33624_title, R.string.ra_33624_text, 10, true, "remake-legends"),
    AchievementDefinition(195144, 10, R.string.ra_195144_title, R.string.ra_195144_text, 3, false, "remake-brock"),
    AchievementDefinition(195145, 10, R.string.ra_195145_title, R.string.ra_195145_text, 3, false, "remake-brock"),
    AchievementDefinition(195148, 10, R.string.ra_195148_title, R.string.ra_195148_text, 3, false, "remake-ship"),
    AchievementDefinition(195149, 10, R.string.ra_195149_title, R.string.ra_195149_text, 3, false, ZARBI_CHAPTER),
    AchievementDefinition(195150, 10, R.string.ra_195150_title, R.string.ra_195150_text, 3, false, "remake-brock"),
    AchievementDefinition(195151, 10, R.string.ra_195151_title, R.string.ra_195151_text, 3, false, "remake-brock"),
    AchievementDefinition(195152, 10, R.string.ra_195152_title, R.string.ra_195152_text, 3, false, "remake-celadon"),
    AchievementDefinition(195154, 10, R.string.ra_195154_title, R.string.ra_195154_text, 5, true, "remake-flute"),
    AchievementDefinition(195155, 10, R.string.ra_195155_title, R.string.ra_195155_text, 3, false, "remake-ship"),
    AchievementDefinition(195156, 10, R.string.ra_195156_title, R.string.ra_195156_text, 5, false, "remake-saffron"),
    AchievementDefinition(195158, 10, R.string.ra_195158_title, R.string.ra_195158_text, 3, false, "remake-saffron"),
    AchievementDefinition(195163, 10, R.string.ra_195163_title, R.string.ra_195163_text, 3, false, "remake-flute"),
    AchievementDefinition(195164, 10, R.string.ra_195164_title, R.string.ra_195164_text, 3, false, "remake-cinnabar"),
    AchievementDefinition(195165, 10, R.string.ra_195165_title, R.string.ra_195165_text, 3, false, "remake-cinnabar"),
    AchievementDefinition(195167, 10, R.string.ra_195167_title, R.string.ra_195167_text, 5, false, "remake-sapphire"),
    AchievementDefinition(195168, 10, R.string.ra_195168_title, R.string.ra_195168_text, 3, false, "remake-cinnabar"),
    AchievementDefinition(195169, 10, R.string.ra_195169_title, R.string.ra_195169_text, 3, false, "remake-misty"),
    AchievementDefinition(33625, 10, R.string.ra_33625_title, R.string.ra_33625_text, 50, true, COLLECTION_CHAPTER)
)

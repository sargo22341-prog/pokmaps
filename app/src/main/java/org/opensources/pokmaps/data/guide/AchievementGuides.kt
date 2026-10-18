package org.opensources.pokmaps.data.guide

import android.content.Context
import android.content.res.Resources
import android.util.TypedValue
import androidx.annotation.ArrayRes
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.CaptureGoals
import org.opensources.pokmaps.domain.guide.GuideCategory
import org.opensources.pokmaps.domain.model.GameVersion
import org.opensources.pokmaps.domain.model.VersionGroup

/** Métadonnées et textes compilés depuis les archives et CSV, sans copie Kotlin par succès. */
internal fun achievementGuides(context: Context, versionId: Int): List<GuideDefinition> {
    val version = GameVersion.of(versionId)

    @ArrayRes val array = when (version) {
        GameVersion.DIAMOND, GameVersion.PEARL, GameVersion.PLATINUM -> return emptyList()
        GameVersion.RED -> R.array.achievements_1
        GameVersion.BLUE -> R.array.achievements_2
        GameVersion.YELLOW -> R.array.achievements_3
        GameVersion.GOLD -> R.array.achievements_4
        GameVersion.SILVER -> R.array.achievements_5
        GameVersion.CRYSTAL -> R.array.achievements_6
        GameVersion.RUBY -> R.array.achievements_7
        GameVersion.SAPPHIRE -> R.array.achievements_8
        GameVersion.EMERALD -> R.array.achievements_9
        GameVersion.FIRERED -> R.array.achievements_10
        GameVersion.LEAFGREEN -> R.array.achievements_11
    }
    return context.resources.obtainTypedArray(array).use { entries ->
        check(entries.length() in 1..500) { "Catalogue de succès invalide : $version" }
        List(entries.length()) { index ->
            readAchievement(context.resources, entries.getResourceId(index, 0), version)
        }
    }
}

private fun readAchievement(resources: Resources, @ArrayRes array: Int, version: GameVersion): GuideDefinition {
    val values = readValues(resources, array)
    val id = values[0].data
    val points = values[3].data
    check(id > 0 && points >= 0 && values[4].data in 0..1) { "Succès invalide : $id" }
    return GuideDefinition(
        "ra-$id", values[1].resourceId, values[2].resourceId, GuideCategory.ACHIEVEMENT,
        setOf(version.id),
        when (version.group) {
            VersionGroup.RED_BLUE, VersionGroup.YELLOW, VersionGroup.FIRERED_LEAFGREEN -> 25
            VersionGroup.DIAMOND_PEARL, VersionGroup.PLATINUM -> 387
            VersionGroup.GOLD_SILVER, VersionGroup.CRYSTAL -> 175
            VersionGroup.RUBY_SAPPHIRE, VersionGroup.EMERALD -> 252
        },
        listOf("https://retroachievements.org/achievement/$id"),
        missable = values[4].data == 1, achievementId = id, points = points,
        chapter = checkNotNull(values[5].string).toString(),
        captureIds = CaptureGoals.forAchievement(id)?.species.orEmpty()
    )
}

private fun readValues(resources: Resources, @ArrayRes array: Int): List<TypedValue> =
    resources.obtainTypedArray(array).use { entries ->
        check(entries.length() == 6) { "Métadonnées de succès incomplètes : $array" }
        val values = List(entries.length()) { index ->
            TypedValue().also { check(entries.getValue(index, it)) { "Colonne absente : $array:$index" } }
        }
        check(listOf(0, 3, 4).all { values[it].type in TypedValue.TYPE_FIRST_INT..TypedValue.TYPE_LAST_INT }) {
            "Colonnes numériques de succès invalides : $array"
        }
        check(listOf(1, 2, 5).all { values[it].type == TypedValue.TYPE_STRING }) {
            "Colonnes textuelles de succès invalides : $array"
        }
        check(values[1].resourceId != 0 && values[2].resourceId != 0) { "Textes de succès absents : $array" }
        values
    }

package org.opensources.pokmaps.data.guide

import androidx.annotation.StringRes
import org.opensources.pokmaps.domain.guide.CaptureGoals
import org.opensources.pokmaps.domain.guide.GuideCategory

internal data class AchievementDefinition(
    val id: Int,
    val version: Int,
    @StringRes val title: Int,
    @StringRes val text: Int,
    val points: Int,
    val missable: Boolean,
    val chapter: String
)

internal fun achievementGuides(): List<GuideDefinition> = (
    redAchievements() + blueAchievements() + yellowAchievements() + goldAchievements() + silverAchievements() +
        crystalAchievements() + rubyAchievements() + sapphireAchievements() + emeraldAchievements() +
        fireRedAchievements() + leafGreenAchievements()
    ).map {
    GuideDefinition(
        "ra-${it.id}", it.title, it.text, GuideCategory.ACHIEVEMENT, setOf(it.version),
        when (it.version) {
            in 1..3, 10, 11 -> 25
            in 4..6 -> 175
            7, 8, 9 -> 252
            else -> error("Version de succès inconnue : ${it.version}")
        },
        listOf("https://retroachievements.org/achievement/${it.id}"),
        missable = it.missable, achievementId = it.id, points = it.points, chapter = it.chapter,
        captureIds = CaptureGoals.forAchievement(it.id)?.species.orEmpty()
    )
}

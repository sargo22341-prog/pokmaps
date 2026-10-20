package org.opensources.pokmaps.data.guide

import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.GuideCategory
import org.opensources.pokmaps.domain.model.Game

internal fun sinnohToolGuides(game: Game): List<GuideDefinition> = listOf(
    GuideDefinition(
        "breeding",
        R.string.guide_breeding_title,
        R.string.guide_breeding_sinnoh_text,
        GuideCategory.TIP,
        setOf(game.versionId),
        440,
        sinnohGuideSources(game)
    ),
    GuideDefinition(
        "friendship",
        R.string.guide_friendship_title,
        R.string.guide_friendship_sinnoh_text,
        GuideCategory.TIP,
        setOf(game.versionId),
        427,
        sinnohGuideSources(game)
    ),
    GuideDefinition(
        "sinnoh-roamers",
        R.string.guide_roamer_sinnoh_title,
        R.string.guide_roamer_sinnoh_text,
        GuideCategory.SIDE_QUEST,
        setOf(game.versionId),
        481,
        sinnohGuideSources(game)
    )
)

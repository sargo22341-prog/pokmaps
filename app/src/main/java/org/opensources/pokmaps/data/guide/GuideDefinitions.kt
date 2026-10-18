package org.opensources.pokmaps.data.guide

import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.VersionGroup

/** Choisit les fournisseurs de la branche du jeu avant de construire les définitions propres à sa version. */
internal fun guideDefinitions(game: Game): List<GuideDefinition> {
    val versionId = game.version.id
    val branch = when (game.versionGroup) {
        VersionGroup.RED_BLUE, VersionGroup.YELLOW -> kantoGuides() + sideGuides() + tipGuides()

        VersionGroup.GOLD_SILVER, VersionGroup.CRYSTAL -> johtoGuides() + sideGuides() + tipGuides()

        VersionGroup.RUBY_SAPPHIRE, VersionGroup.EMERALD ->
            gbaToolGuides() + hoennGuides() + hoennCalendarGuides() + hoennContentGuides()

        VersionGroup.DIAMOND_PEARL, VersionGroup.PLATINUM -> emptyList()

        VersionGroup.FIRERED_LEAFGREEN -> gbaToolGuides() + remakeGuides()
    }
    return branch.filter { versionId in it.versions }
}

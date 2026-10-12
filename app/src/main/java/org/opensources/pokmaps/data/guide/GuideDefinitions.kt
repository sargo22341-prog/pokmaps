package org.opensources.pokmaps.data.guide

/** Choisit les fournisseurs avant de construire les définitions propres au jeu. */
internal fun guideDefinitions(versionId: Int): List<GuideDefinition> {
    val branch = when (versionId) {
        1, 2, 3 -> kantoGuides() + sideGuides() + tipGuides()

        4, 5, 6 -> johtoGuides() + sideGuides() + tipGuides()

        7, 8, 9 -> gbaToolGuides() + hoennGuides() + hoennCalendarGuides() + hoennContentGuides() +
            gbaCollectionGuides(versionId)

        10, 11 -> gbaToolGuides() + remakeGuides() + gbaCollectionGuides(versionId)

        else -> error("Version de guides inconnue : $versionId")
    }
    return branch.filter { versionId in it.versions } + achievementGuides(versionId)
}

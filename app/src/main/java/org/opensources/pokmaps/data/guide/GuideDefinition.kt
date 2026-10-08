package org.opensources.pokmaps.data.guide

import androidx.annotation.StringRes
import org.opensources.pokmaps.domain.guide.GuideCategory

internal data class GuideDefinition(
    val id: String,
    @StringRes val title: Int,
    @StringRes val text: Int,
    val category: GuideCategory,
    val versions: Set<Int>,
    val pokemonId: Int,
    val sources: List<String>,
    val relatedIds: Set<String> = emptySet(),
    val missable: Boolean = false,
    val captureIds: Set<Int> = emptySet(),
    val achievementId: Int? = null,
    val points: Int = 0,
    val chapter: String? = null,
    val shiny: Boolean = false
)

internal val KANTO_VERSIONS = setOf(1, 2, 3)
internal val JOHTO_VERSIONS = setOf(4, 5, 6)
internal const val KANTO_SOURCE = "https://www.eternia.fr/dossier/pokemon-version-rouge-pokemon-version-bleue"
internal const val JOHTO_SOURCE = "https://www.eternia.fr/dossier/pokemon-version-or-pokemon-version-argent"

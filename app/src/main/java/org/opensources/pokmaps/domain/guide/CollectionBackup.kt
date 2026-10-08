package org.opensources.pokmaps.domain.guide

import org.opensources.pokmaps.domain.pokemon.UnownForm

data class CollectionBackup(
    val favorites: Set<Int>,
    val caught: Map<Int, Set<Int>>,
    val guides: Map<Int, GuideProgress>,
    val unown: Map<Int, Set<UnownForm>> = emptyMap()
) {
    init {
        require(favorites.all { it in 1..251 })
        require(caught.keys.all { it in 1..6 })
        require(caught.all { (version, ids) -> ids.all { it in 1..if (version <= 3) 151 else 251 } })
        require(guides.keys.all { it in 1..6 })
        guides.forEach { (version, progress) -> validateGuideProgress(version, progress) }
        require(unown.keys.all { it in 4..6 })
        require(unown.values.all { forms -> forms.all { it in UnownForm.available(2) } })
    }
}

fun validateGuideProgress(version: Int, progress: GuideProgress) {
    require(version in 1..6)
    require(progress.completed.size <= 500 && progress.completed.all { it.matches(ARTICLE_ID) })
    require(
        progress.roamers.size <= 3 && progress.roamers.map {
            it.pokemonId
        }.distinct().size == progress.roamers.size
    )
    require(
        progress.roamers.all {
            version in 4..6 && it.pokemonId in Roamers.pokemonIds && it.place in Roamers.places &&
                (version != 6 || it.pokemonId != 245)
        }
    )
}

private val ARTICLE_ID = Regex("[a-z0-9-]{1,100}")

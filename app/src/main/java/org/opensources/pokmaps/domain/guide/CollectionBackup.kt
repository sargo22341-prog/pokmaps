package org.opensources.pokmaps.domain.guide

import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.pokemon.UnownForm

data class CollectionBackup(
    val favorites: Set<Int>,
    val caught: Map<Int, Set<Int>>,
    val guides: Map<Int, GuideProgress>,
    val unown: Map<Int, Set<UnownForm>> = emptyMap()
) {
    init {
        require(favorites.all { it in 1..386 })
        require(caught.keys.all { it > 0 })
        require(caught.values.all { ids -> ids.all { it in 1..386 } })
        require(guides.keys.all { it > 0 })
        guides.forEach { (version, progress) -> validateGuideProgress(version, progress) }
        require(unown.keys.all { it > 0 })
    }
}

fun validateGuideProgress(version: Int, progress: GuideProgress) {
    require(version > 0)
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

/** Les versions et leurs limites viennent du catalogue embarqué, y compris lors d'un import ancien. */
fun validateCollectionBackup(backup: CollectionBackup, games: List<Game>) {
    val catalog = games.associateBy { it.versionId }
    require((backup.caught.keys + backup.guides.keys + backup.unown.keys).all { it in catalog }) {
        "Version de sauvegarde absente de la base"
    }
    backup.caught.forEach { (version, ids) ->
        val generation = catalog.getValue(version).generationId
        val maximum = when (generation) {
            1 -> 151
            2 -> 251
            3 -> 386
            else -> error("Génération non prise en charge : $generation")
        }
        require(ids.all { it <= maximum }) { "Espèce absente de la génération : $version" }
    }
    backup.unown.forEach { (version, forms) ->
        require(forms.all { it in UnownForm.available(catalog.getValue(version)) }) {
            "Forme de Zarbi absente du jeu : $version"
        }
    }
}

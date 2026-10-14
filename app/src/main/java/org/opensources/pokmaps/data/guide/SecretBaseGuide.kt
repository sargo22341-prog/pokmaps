package org.opensources.pokmaps.data.guide

import android.content.Context
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.GuideArticle
import org.opensources.pokmaps.domain.guide.GuideCategory
import org.opensources.pokmaps.domain.guide.GuideSpan
import org.opensources.pokmaps.domain.guide.GuideTarget
import org.opensources.pokmaps.domain.map.MapCatalog

/** Toutes les Bases Secrètes du jeu, par lieu ; chaque base ouvre son entrée sur la carte. Null sans base. */
internal fun secretBaseGuide(context: Context, catalog: MapCatalog): GuideArticle? {
    if (catalog.secretBases.isEmpty()) return null
    val places = catalog.secretBases.groupBy { it.placeId }.values.map { bases ->
        val spans = mutableListOf(
            GuideSpan(context.getString(R.string.guide_secret_bases_place, bases.first().placeName, bases.size))
        )
        bases.forEachIndexed { index, base ->
            if (index > 0) spans += GuideSpan(context.getString(R.string.guide_secret_bases_separator))
            spans += GuideSpan(base.baseName, GuideTarget.SecretBase(base.entrance.id))
        }
        spans.toList()
    }
    return GuideArticle(
        "hoenn-secret-bases",
        context.getString(R.string.guide_secret_bases_title),
        GuideCategory.TIP,
        listOf(listOf(GuideSpan(context.getString(R.string.guide_secret_bases_intro, catalog.secretBases.size)))) +
            places,
        263,
        listOf(
            "https://github.com/pret/pokeruby/blob/5784633ce4ef/src/secret_base.c",
            "https://github.com/pret/pokeemerald/blob/731ad5bfd6e6/src/secret_base.c"
        )
    )
}

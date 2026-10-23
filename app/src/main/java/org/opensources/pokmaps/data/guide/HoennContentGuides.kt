package org.opensources.pokmaps.data.guide

import android.content.Context
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.GuideArticle
import org.opensources.pokmaps.domain.guide.GuideCategory
import org.opensources.pokmaps.domain.guide.GuideSpan
import org.opensources.pokmaps.domain.guide.GuideTarget
import org.opensources.pokmaps.domain.hoenn.DecorationSource
import org.opensources.pokmaps.domain.hoenn.HoennContent
import org.opensources.pokmaps.domain.map.MapCatalog
import org.opensources.pokmaps.domain.map.OfferCurrency
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.VersionGroup

internal fun hoennContentGuides(): List<GuideDefinition> {
    val versions = RUBY_SAPPHIRE_VERSIONS + EMERALD_VERSIONS
    val sources = listOf(
        "https://github.com/pret/pokeruby/tree/5784633ce4ef/src",
        "https://github.com/pret/pokeemerald/tree/731ad5bfd6e6/src"
    )
    return listOf(
        GuideDefinition(
            "hoenn-berries",
            R.string.guide_berries_title,
            R.string.guide_berries_text,
            GuideCategory.TIP,
            versions,
            315,
            sources
        ),
        GuideDefinition(
            "hoenn-contests",
            R.string.contest_title,
            R.string.guide_contests_text,
            GuideCategory.SIDE_QUEST,
            versions,
            300,
            sources
        ),
        GuideDefinition(
            "hoenn-pokeblocks",
            R.string.guide_pokeblocks_title,
            R.string.guide_pokeblocks_text,
            GuideCategory.TIP,
            versions,
            349,
            sources
        )
    )
}

internal fun decorationGuide(context: Context, game: Game, catalog: MapCatalog, content: HoennContent): GuideArticle {
    val source = when (game.versionGroup) {
        VersionGroup.HEARTGOLD_SOULSILVER -> error("Décorations hors Hoenn")

        VersionGroup.RUBY_SAPPHIRE -> "https://github.com/pret/pokeruby/blob/5784633ce4ef/src/decoration.c"

        VersionGroup.EMERALD -> "https://github.com/pret/pokeemerald/blob/731ad5bfd6e6/src/data/decoration/header.h"

        VersionGroup.RED_BLUE, VersionGroup.YELLOW, VersionGroup.GOLD_SILVER, VersionGroup.CRYSTAL,
        VersionGroup.FIRERED_LEAFGREEN, VersionGroup.DIAMOND_PEARL, VersionGroup.PLATINUM -> error(
            "Décorations hors de Hoenn : ${game.versionIdentifier}"
        )
    }
    val paragraphs = listOf(listOf(GuideSpan(context.getString(R.string.guide_decorations_intro)))) +
        content.decorations.map { decoration ->
            val sources = content.sources.filter {
                it.identifier == decoration.identifier && it.version == game.versionIdentifier
            }.distinctBy { Triple(it.map, it.gift, it.price) }
            val heading = context.getString(R.string.decoration_details, decoration.name, decoration.shape)
            val spans = mutableListOf(GuideSpan(heading))
            if (sources.isEmpty()) spans += GuideSpan(context.getString(R.string.decoration_special))
            sources.forEach { source ->
                val map =
                    requireNotNull(catalog.mapByIdentifier(source.map)) { "Décoration : lieu absent : ${source.map}" }
                spans += GuideSpan(decorationSourceText(context, source, decoration.price))
                spans += GuideSpan(map.name, GuideTarget.Place(map.identifier))
                spans += GuideSpan("\n")
            }
            spans.toList()
        }
    return GuideArticle(
        "hoenn-decorations",
        context.getString(R.string.guide_decorations_title),
        GuideCategory.SIDE_QUEST,
        paragraphs,
        352,
        listOf(source)
    )
}

private fun decorationSourceText(context: Context, source: DecorationSource, defaultPrice: Int): String {
    if (source.gift) return context.getString(R.string.decoration_gift)
    val price = source.price ?: defaultPrice
    val cost = when (source.currency) {
        OfferCurrency.MONEY -> context.getString(R.string.map_offer_price, price)

        OfferCurrency.COINS -> context.resources.getQuantityString(R.plurals.coins, price, price)

        OfferCurrency.BATTLE_POINTS -> context.resources.getQuantityString(
            R.plurals.map_offer_battle_points,
            price,
            price
        )

        OfferCurrency.ASHES -> context.resources.getQuantityString(R.plurals.map_offer_ashes, price, price)
    }
    return context.getString(R.string.decoration_purchase, cost)
}

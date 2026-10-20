package org.opensources.pokmaps.data.guide

import android.content.Context
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.GuideArticle
import org.opensources.pokmaps.domain.guide.GuideSpan
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.sinnoh.SinnohUnderground
import org.opensources.pokmaps.domain.sinnoh.UndergroundGood
import org.opensources.pokmaps.domain.sinnoh.UndergroundPrice

internal fun sinnohUndergroundArticles(context: Context, game: Game, content: SinnohUnderground): List<GuideArticle> =
    listOf(
        miningArticle(context, game, content),
        goodsArticle(context, game, content),
        trapsArticle(context, game, content)
    )

private fun miningArticle(context: Context, game: Game, content: SinnohUnderground): GuideArticle =
    sinnohContentArticle(
        context,
        game,
        "sinnoh-mining",
        context.getString(R.string.sinnoh_mining_title),
        if (game.versionId == 14) R.string.sinnoh_mining_pt_intro else R.string.sinnoh_mining_dp_intro,
        content.mining.filter { it.weights.any { weight -> weight > 0 } }.map { row ->
            listOf(
                GuideSpan(
                    context.getString(
                        R.string.sinnoh_mining_row,
                        row.name,
                        row.weights[0],
                        row.weights[1],
                        row.weights[2],
                        row.weights[3]
                    )
                )
            )
        }
    )

private fun goodsArticle(context: Context, game: Game, content: SinnohUnderground): GuideArticle = sinnohContentArticle(
    context,
    game,
    "sinnoh-goods",
    context.getString(R.string.sinnoh_goods_title),
    R.string.sinnoh_goods_intro,
    content.goods.filter { it.available }.map { row ->
        listOf(
            GuideSpan(
                context.getString(
                    R.string.sinnoh_good_row,
                    row.name,
                    row.width,
                    row.depth,
                    goodSources(context, row),
                    if (row.national) {
                        context.getString(R.string.sinnoh_national)
                    } else {
                        ""
                    }
                )
            )
        )
    }
)

private fun trapsArticle(context: Context, game: Game, content: SinnohUnderground): GuideArticle = sinnohContentArticle(
    context,
    game,
    "sinnoh-traps",
    context.getString(R.string.sinnoh_traps_title),
    R.string.sinnoh_traps_intro,
    content.traps.map { row ->
        listOf(
            GuideSpan(
                context.getString(R.string.sinnoh_trap_row, row.name, undergroundPrice(context, row.price))
            )
        )
    }
)

private fun goodSources(context: Context, good: UndergroundGood): String {
    val sources = buildList {
        if (good.price.sphere != 0) {
            add(
                context.getString(
                    R.string.sinnoh_good_vendor,
                    undergroundPrice(context, good.price)
                )
            )
        }
        if (good.money > 0) add(context.getString(R.string.sinnoh_good_store, good.money))
        if (good.id in setOf(9, 11, 17, 101, 102, 103, 113) || good.id in 81..84) {
            add(context.getString(R.string.sinnoh_good_eterna))
        }
        if (good.id in 46..47 || good.id in 72..80) add(context.getString(R.string.sinnoh_good_hearthome))
        if (good.id in 85..87) add(context.getString(R.string.sinnoh_good_tower))
        if (good.id == 118) add(context.getString(R.string.sinnoh_good_external))
    }
    require(sources.isNotEmpty()) { "Mobilier sans provenance : ${good.id}" }
    return sources.joinToString(context.getString(R.string.sinnoh_list_separator))
}

private fun undergroundPrice(context: Context, price: UndergroundPrice): String {
    val sphere = when (price.sphere) {
        1 -> R.string.sinnoh_sphere_prism
        2 -> R.string.sinnoh_sphere_pale
        3 -> R.string.sinnoh_sphere_red
        4 -> R.string.sinnoh_sphere_blue
        5 -> R.string.sinnoh_sphere_green
        6 -> R.string.sinnoh_sphere_random
        else -> error("Prix sans sphère : ${price.sphere}")
    }
    return context.getString(
        R.string.sinnoh_sphere_price,
        context.getString(sphere),
        price.minimum,
        price.maximumExclusive - 1
    )
}

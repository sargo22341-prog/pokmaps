package org.opensources.pokmaps.data.guide

import android.content.Context
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.GuideArticle
import org.opensources.pokmaps.domain.guide.GuideSpan
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.sinnoh.FactoryPool
import org.opensources.pokmaps.domain.sinnoh.SinnohBattles
import org.opensources.pokmaps.domain.sinnoh.SinnohFrontier

internal fun factoryArticles(
    context: Context,
    game: Game,
    battles: SinnohBattles,
    frontier: SinnohFrontier
): List<GuideArticle> = (0..7).map { index ->
    val paragraphs = rentalParagraphs(context, R.string.sinnoh_factory_level50, frontier.level50, index, battles) +
        rentalParagraphs(context, R.string.sinnoh_factory_open_player, frontier.openPlayer, index, battles) +
        opponentParagraphs(context, R.string.sinnoh_factory_opponent50, frontier.level50, index, battles, frontier) +
        opponentParagraphs(
            context,
            R.string.sinnoh_factory_open_opponent,
            frontier.openOpponent,
            index,
            battles,
            frontier
        )
    sinnohContentArticle(
        context,
        game,
        "sinnoh-factory-${index + 1}",
        context.getString(R.string.sinnoh_battle_series, context.getString(R.string.sinnoh_factory), index + 1),
        R.string.sinnoh_factory_intro,
        paragraphs
    )
}

private fun rentalParagraphs(
    context: Context,
    title: Int,
    pools: List<FactoryPool>,
    index: Int,
    battles: SinnohBattles
): List<List<GuideSpan>> = factoryParagraphs(context, title, pools[index], battles) +
    if (pools[index].upgrade) {
        factoryParagraphs(context, R.string.sinnoh_factory_upgrade, pools[index + 1], battles)
    } else {
        emptyList()
    }

private fun opponentParagraphs(
    context: Context,
    title: Int,
    pools: List<FactoryPool>,
    index: Int,
    battles: SinnohBattles,
    frontier: SinnohFrontier
): List<List<GuideSpan>> {
    val series = frontier.factory[index]
    val possiblePools = (series.ordinary.toList() + series.last.toList())
        .map { trainer -> pools.first { trainer < it.trainerLimit } }.distinct()
    return possiblePools.flatMap { pool ->
        val position = pools.indexOf(pool)
        factoryParagraphs(context, title, pool, battles) +
            if (pool.upgrade) {
                factoryParagraphs(context, R.string.sinnoh_factory_upgrade, pools[position + 1], battles)
            } else {
                emptyList()
            }
    }
}

internal fun factoryChampionParagraphs(
    context: Context,
    battles: SinnohBattles,
    frontier: SinnohFrontier
): List<List<GuideSpan>> = listOf(
    R.string.sinnoh_cardus_silver50 to frontier.level50[8],
    R.string.sinnoh_cardus_gold50 to frontier.level50[9],
    R.string.sinnoh_cardus_silver_open to frontier.openOpponent[8],
    R.string.sinnoh_cardus_gold_open to frontier.openOpponent[9]
).flatMap { (title, pool) -> factoryParagraphs(context, title, pool, battles) }

private fun factoryParagraphs(
    context: Context,
    title: Int,
    pool: FactoryPool,
    battles: SinnohBattles
): List<List<GuideSpan>> = listOf(
    listOf(
        GuideSpan(
            context.getString(
                R.string.sinnoh_factory_pool,
                context.getString(title),
                pool.ivs
            )
        )
    )
) +
    (pool.first..pool.last).map { configurationParagraph(context, battles.configurations.getValue(it)) }

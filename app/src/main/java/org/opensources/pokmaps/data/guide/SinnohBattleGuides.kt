package org.opensources.pokmaps.data.guide

import android.content.Context
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.GuideArticle
import org.opensources.pokmaps.domain.guide.GuideSpan
import org.opensources.pokmaps.domain.guide.GuideTarget
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.sinnoh.BattleConfiguration
import org.opensources.pokmaps.domain.sinnoh.BattleSeries
import org.opensources.pokmaps.domain.sinnoh.SinnohBattles
import org.opensources.pokmaps.domain.sinnoh.SinnohFrontier

internal fun sinnohBattleArticles(context: Context, game: Game, battles: SinnohBattles): List<GuideArticle> {
    val tower = seriesArticles(context, game, battles, "tower", R.string.sinnoh_tower, battles.tower)
    val bosses = listOf(championArticle(context, game, battles))
    val frontier = battles.frontier ?: return tower + bosses
    return tower + bosses +
        seriesArticles(context, game, battles, "castle", R.string.sinnoh_castle, frontier.castle) +
        seriesArticles(context, game, battles, "arcade", R.string.sinnoh_arcade, frontier.arcade) +
        factoryArticles(context, game, battles, frontier) + hallArticles(context, game, frontier)
}

private fun seriesArticles(
    context: Context,
    game: Game,
    battles: SinnohBattles,
    key: String,
    name: Int,
    series: List<BattleSeries>
): List<GuideArticle> = series.map { row ->
    sinnohContentArticle(
        context,
        game,
        "sinnoh-$key-${row.number}",
        context.getString(R.string.sinnoh_battle_series, context.getString(name), row.number),
        if (key == "arcade") R.string.sinnoh_arcade_pool_intro else R.string.sinnoh_battle_pool_intro,
        listOf(listOf(GuideSpan(context.getString(R.string.sinnoh_battle_ordinary)))) +
            battles.possibilities(row.ordinary).map { configurationParagraph(context, it, key != "arcade") } +
            listOf(listOf(GuideSpan(context.getString(R.string.sinnoh_battle_final)))) +
            battles.possibilities(row.last).map { configurationParagraph(context, it, key != "arcade") }
    )
}

private fun championArticle(context: Context, game: Game, battles: SinnohBattles): GuideArticle {
    val names = listOf(305 to R.string.sinnoh_koner_silver, 306 to R.string.sinnoh_koner_gold) +
        if (battles.frontier == null) {
            emptyList()
        } else {
            listOf(
                311 to R.string.sinnoh_dahlia_silver,
                312 to R.string.sinnoh_dahlia_gold,
                313 to R.string.sinnoh_parsley_silver,
                314 to R.string.sinnoh_parsley_gold
            )
        }
    val paragraphs = names.flatMap { (trainer, title) ->
        listOf(listOf(GuideSpan(context.getString(title)))) +
            battles.trainers[trainer].map {
                configurationParagraph(context, battles.configurations.getValue(it), trainer !in 311..312)
            }
    }
    return sinnohContentArticle(
        context,
        game,
        "sinnoh-brains",
        context.getString(R.string.sinnoh_brains_title),
        R.string.sinnoh_brains_intro,
        paragraphs + battles.frontier?.let { factoryChampionParagraphs(context, battles, it) }.orEmpty()
    )
}

private fun hallArticles(context: Context, game: Game, frontier: SinnohFrontier): List<GuideArticle> =
    frontier.hallRanks.mapIndexed { index, range ->
        sinnohContentArticle(
            context,
            game,
            "sinnoh-hall-${index + 1}",
            context.getString(R.string.sinnoh_hall_rank, index + 1),
            R.string.sinnoh_hall_intro,
            frontier.hall.filter { it.id in range }.map { configurationParagraph(context, it) }
        )
    }

internal fun configurationParagraph(
    context: Context,
    row: BattleConfiguration,
    keepsItem: Boolean = true
): List<GuideSpan> = listOf(
    GuideSpan(
        context.getString(R.string.sinnoh_configuration_name, row.id, row.name),
        GuideTarget.Pokemon(row.species)
    ),
    GuideSpan(
        context.getString(
            R.string.sinnoh_configuration_details,
            row.nature,
            row.item.takeIf { keepsItem }.orEmpty().ifBlank { context.getString(R.string.sinnoh_no_item) },
            row.moveNames.joinToString(context.getString(R.string.sinnoh_list_separator)),
            evNames(context, row.evs)
        )
    )
)

private fun evNames(context: Context, flags: Int): String {
    val names = listOf(
        R.string.breeding_iv_hp,
        R.string.breeding_iv_attack,
        R.string.breeding_iv_defense,
        R.string.breeding_iv_speed,
        R.string.breeding_iv_special_attack,
        R.string.breeding_iv_special_defense
    )
    return names.filterIndexed { index, _ -> flags and (1 shl index) != 0 }
        .joinToString(context.getString(R.string.sinnoh_list_separator)) { context.getString(it) }
}

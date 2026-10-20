package org.opensources.pokmaps.data.guide

import android.content.Context
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.GuideArticle
import org.opensources.pokmaps.domain.guide.GuideCategory
import org.opensources.pokmaps.domain.guide.GuideSpan
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.VersionGroup
import org.opensources.pokmaps.domain.sinnoh.SinnohContent

internal fun sinnohContentDefinitions(game: Game): List<GuideDefinition> = listOf(
    Triple("sinnoh-berries", R.string.sinnoh_berries_title, R.string.sinnoh_berries_text),
    Triple("sinnoh-super-contests", R.string.super_contest_title, R.string.sinnoh_contests_text),
    Triple("sinnoh-poffins", R.string.sinnoh_poffins_title, R.string.sinnoh_poffins_text),
    Triple("sinnoh-underground", R.string.sinnoh_underground_title, R.string.sinnoh_underground_text),
    Triple(
        "sinnoh-battle",
        R.string.sinnoh_battle_title,
        if (game.versionGroup ==
            VersionGroup.PLATINUM
        ) {
            R.string.sinnoh_battle_pt_text
        } else {
            R.string.sinnoh_battle_dp_text
        }
    )
).map { (id, title, text) ->
    GuideDefinition(id, title, text, GuideCategory.SIDE_QUEST, setOf(game.versionId), 387, sinnohContentSources(game))
}

internal fun sinnohContentArticles(context: Context, game: Game, content: SinnohContent): List<GuideArticle> =
    sinnohUndergroundArticles(context, game, content.underground) +
        sinnohBattleArticles(context, game, content.battles)

internal fun sinnohContentArticle(
    context: Context,
    game: Game,
    id: String,
    title: String,
    introduction: Int,
    paragraphs: List<List<GuideSpan>>
): GuideArticle = GuideArticle(
    id,
    title,
    GuideCategory.SIDE_QUEST,
    listOf(
        listOf(GuideSpan(context.getString(introduction))),
        listOf(GuideSpan(context.getString(R.string.sinnoh_content_version, game.name))),
        listOf(GuideSpan(context.getString(R.string.sinnoh_content_no_prediction)))
    ) + paragraphs,
    387,
    sinnohContentSources(game),
    setOf("sinnoh-underground", "sinnoh-battle")
)

private fun sinnohContentSources(game: Game): List<String> {
    val platinum = game.versionGroup == VersionGroup.PLATINUM
    val root = if (platinum) {
        "https://github.com/pret/pokeplatinum/blob/1dc13dcea40c04ab53f1f607de46023dc409ef20/"
    } else {
        "https://github.com/pret/pokediamond/blob/b623abef1b4dfe204ca50aab42447ac00c134290/"
    }
    val files = if (platinum) {
        listOf(
            "src/berry_patches.c", "res/items/data/cheri_berry.json", "src/unk_02094EDC.c",
            "src/poffin.c", "src/underground/mining.c", "src/underground/vendors.c", "src/goods.c",
            "src/unk_0204AEE8.c", "src/overlay104/battle_factory_helpers.c",
            "src/overlay104/battle_hall_helpers.c", "src/overlay104/battle_castle_helpers.c",
            "src/overlay104/battle_arcade_helpers.c"
        )
    } else {
        listOf(
            "files/itemtool/itemdata/nuts_data.json",
            "files/poketool/waza/waza_tbl.json",
            "arm9/overlays/18/asm/overlay_18.s",
            "arm9/asm/unk_0204CA80.s",
            "arm9/overlays/06/asm/overlay_06.s",
            "files/battle/b_tower/btdpm/narc_0001.bin"
        )
    }
    return files.map { root + it }
}

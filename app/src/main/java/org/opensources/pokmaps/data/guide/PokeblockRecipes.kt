package org.opensources.pokmaps.data.guide

import android.content.Context
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.GuideArticle
import org.opensources.pokmaps.domain.guide.GuideCategory
import org.opensources.pokmaps.domain.guide.GuideSpan
import org.opensources.pokmaps.domain.guide.GuideTarget
import org.opensources.pokmaps.domain.hoenn.Berry
import org.opensources.pokmaps.domain.hoenn.HoennContent
import org.opensources.pokmaps.domain.hoenn.Pokeblock
import org.opensources.pokmaps.domain.hoenn.blendPokeblock
import org.opensources.pokmaps.domain.map.GameIndex

internal fun pokeblockRecipes(context: Context, content: HoennContent, index: GameIndex): GuideArticle {
    val cheri = content.berries.getValue("cheri-berry")
    val paragraphs = listOf(listOf(GuideSpan(context.getString(R.string.pokeblock_recipes_intro)))) +
        content.berries.values.map { berry ->
            val result = blendPokeblock(listOf(cheri, berry))
            val text = when (result) {
                is Pokeblock.Black -> context.getString(R.string.pokeblock_black, result.feel)

                is Pokeblock.Recipe -> context.getString(
                    R.string.pokeblock_recipe,
                    result.flavors[0],
                    result.flavors[1],
                    result.flavors[2],
                    result.flavors[3],
                    result.flavors[4],
                    result.feel,
                    result.level
                )
            }
            val target = index.items.firstOrNull { it.identifier == berry.identifier }?.let {
                GuideTarget.Item(it.identifier)
            }
            listOf(GuideSpan(berry.name, target), GuideSpan(berryProfile(context, berry)), GuideSpan(text))
        }
    return GuideArticle(
        "hoenn-pokeblock-recipes",
        context.getString(R.string.pokeblock_recipes_title),
        GuideCategory.TIP,
        paragraphs,
        349,
        listOf("https://github.com/pret/pokeemerald/blob/731ad5bfd6e6/src/berry_blender.c")
    )
}

private fun berryProfile(context: Context, berry: Berry): String {
    val growth = context.getString(
        R.string.berry_growth,
        berry.stageHours,
        berry.stageHours * 4,
        berry.minYield,
        berry.maxYield
    )
    val flavors = context.getString(
        R.string.berry_flavors,
        berry.flavors[0],
        berry.flavors[1],
        berry.flavors[2],
        berry.flavors[3],
        berry.flavors[4]
    )
    return context.getString(R.string.berry_recipe_profile, growth, flavors, berry.smoothness)
}

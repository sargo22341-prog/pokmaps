package org.opensources.pokmaps.data.guide

import android.content.res.Resources
import org.json.JSONArray
import org.json.JSONObject
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.CaptureGoal
import org.opensources.pokmaps.domain.guide.GuideCategory
import org.opensources.pokmaps.domain.model.Game

/** Les textes viennent des ressources compilées, les identifiants des catalogues HGSS validés. */
internal fun hgssGuides(resources: Resources, game: Game): List<GuideDefinition> {
    val metadata = resources.getStringArray(R.array.hgss_guide_metadata)
    require(metadata.size in 1..800)
    val titles = resources.obtainTypedArray(R.array.hgss_guide_titles)
    val texts = resources.obtainTypedArray(R.array.hgss_guide_texts)
    try {
        require(titles.length() == metadata.size && texts.length() == metadata.size)
        return metadata.mapIndexedNotNull { index, raw ->
            val row = JSONObject(raw)
            if (game.versionId !in row.getJSONArray("versions").integers()) return@mapIndexedNotNull null
            val title = titles.getResourceId(index, 0)
            val text = texts.getResourceId(index, 0)
            require(title != 0 && text != 0)
            hgssDefinition(row, game, title, text)
        }
    } finally {
        titles.recycle()
        texts.recycle()
    }
}

private fun hgssDefinition(row: JSONObject, game: Game, title: Int, text: Int): GuideDefinition {
    val captures = row.getJSONArray("captures").integers()
    return GuideDefinition(
        id = row.getString("id"),
        title = title,
        text = text,
        category = GuideCategory.valueOf(row.getString("category")),
        versions = setOf(game.versionId),
        pokemonId = game.mascotPokemonId,
        sources = row.getJSONArray("sources").strings().map { HGSS_SOURCE + it },
        relatedIds = row.getJSONArray("related").strings().toSet(),
        captureGoal = if (captures.isEmpty()) null else CaptureGoal(captures, emptyList()),
        unownGoal = row.getString("id") == "hgss-q-alph"
    )
}

private fun JSONArray.strings(): List<String> = (0 until length()).map(::getString)

private fun JSONArray.integers(): Set<Int> = (0 until length()).map(::getInt).toSet()

private const val HGSS_SOURCE =
    "https://github.com/pret/pokeheartgold/blob/6988158691eb6178cff697cda0428045ddcba5fb/"

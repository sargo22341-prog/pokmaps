package org.opensources.pokmaps.data.repository

import android.content.Context
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import org.opensources.pokmaps.domain.hoenn.Berry
import org.opensources.pokmaps.domain.hoenn.ContestCategory
import org.opensources.pokmaps.domain.hoenn.ContestMove
import org.opensources.pokmaps.domain.hoenn.Decoration
import org.opensources.pokmaps.domain.hoenn.DecorationSource
import org.opensources.pokmaps.domain.hoenn.HoennContent
import org.opensources.pokmaps.domain.model.Game

@Singleton
class HoennRepository(private val read: () -> String) {
    @Inject
    constructor(@ApplicationContext context: Context) : this({
        context.assets.open("hoenn.json").use { stream ->
            val bytes = stream.readNBytes(MAX_BYTES + 1)
            require(bytes.size <= MAX_BYTES) { "Catalogue Hoenn trop volumineux" }
            bytes.toString(Charsets.UTF_8)
        }
    })

    private val mutex = Mutex()
    private var content: Map<String, HoennContent>? = null

    suspend fun content(game: Game): HoennContent? {
        if (game.versionGroupIdentifier !in GROUPS) return null
        return withContext(Dispatchers.IO) {
            mutex.withLock {
                val loaded = content ?: parse(read()).also { content = it }
                requireNotNull(loaded[game.versionGroupIdentifier])
            }
        }
    }

    private fun parse(text: String): Map<String, HoennContent> {
        require(text.length <= MAX_BYTES)
        val root = JSONObject(text)
        require(root.getInt("schema") == 1)
        val groups = root.getJSONObject("groups")
        require(groups.keys().asSequence().toSet() == GROUPS)
        return GROUPS.associateWith { group ->
            val value = groups.getJSONObject(group)
            val berries = rows(value.getJSONArray("berries"), 43).map(::berry)
            val moves = rows(value.getJSONArray("moves"), 354)
            val decorations = rows(value.getJSONArray("decorations"), 120).map { row ->
                Decoration(
                    row.getString("identifier"),
                    row.getString("name"),
                    row.getString("shape").removePrefix("DECORSHAPE_"),
                    row.getInt("price")
                )
            }
            val sources = rows(value.getJSONArray("sources")).map { row ->
                val kind = row.getString("kind")
                require(kind in setOf("sale_decoration", "gift_decoration"))
                DecorationSource(
                    row.getString("identifier"),
                    row.getString("version"),
                    row.getString("map"),
                    kind == "gift_decoration",
                    if (row.isNull("price")) null else row.getInt("price"),
                    org.opensources.pokmaps.domain.map.OfferCurrency.from(row.getString("currency"))
                )
            }
            require(berries.map { it.identifier }.distinct().size == 43)
            require(moves.map { it.getInt("id") }.toSet() == (1..354).toSet())
            require(decorations.map { it.identifier }.distinct().size == 120)
            require(sources.all { source -> decorations.any { it.identifier == source.identifier } })
            HoennContent(
                berries.associateBy { it.identifier },
                moves.associate { it.getInt("id") to move(it) },
                decorations,
                sources
            )
        }
    }

    private fun berry(row: JSONObject): Berry = Berry(
        row.getString("identifier"),
        row.getString("name"),
        row.getInt("stage_hours"),
        row.getInt("min_yield"),
        row.getInt("max_yield"),
        row.getInt("smoothness"),
        row.getJSONArray("flavors").let { array ->
            require(array.length() == 5)
            List(5) { array.getInt(it) }
        }
    )

    private fun move(row: JSONObject): ContestMove = ContestMove(
        ContestCategory.valueOf(row.getString("category")),
        row.getInt("appeal"),
        row.getInt("jam"),
        row.getString("effect"),
        row.getJSONArray("previous").let { array ->
            require(array.length() <= 4)
            List(array.length()) { array.getString(it) }
        }
    )

    private fun rows(array: JSONArray, count: Int? = null): List<JSONObject> {
        require(array.length() in 1..MAX_ROWS && (count == null || array.length() == count))
        return List(array.length()) { array.getJSONObject(it) }
    }

    private companion object {
        const val MAX_BYTES = 512 * 1024
        const val MAX_ROWS = 4096
        val GROUPS = setOf("ruby-sapphire", "emerald")
    }
}

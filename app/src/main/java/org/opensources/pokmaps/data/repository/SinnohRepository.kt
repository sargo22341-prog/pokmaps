package org.opensources.pokmaps.data.repository

import android.content.Context
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import org.json.JSONObject
import org.opensources.pokmaps.domain.hoenn.ContestCategory
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.sinnoh.SinnohBerry
import org.opensources.pokmaps.domain.sinnoh.SinnohContent
import org.opensources.pokmaps.domain.sinnoh.SuperContestMove

@Singleton
class SinnohRepository(private val read: () -> String) {
    @Inject
    constructor(@ApplicationContext context: Context) : this({
        context.assets.open("sinnoh.json").use { stream ->
            val bytes = stream.readNBytes(MAX_BYTES + 1)
            require(bytes.size <= MAX_BYTES) { "Catalogue Sinnoh trop volumineux" }
            bytes.toString(Charsets.UTF_8)
        }
    })

    private val mutex = Mutex()
    private var cache: Map<String, SinnohContent>? = null

    suspend fun content(game: Game): SinnohContent? {
        if (game.versionGroupIdentifier !in GROUPS) return null
        return withContext(Dispatchers.IO) {
            mutex.withLock {
                val loaded = cache ?: parse(read()).also { cache = it }
                loaded.getValue(game.versionGroupIdentifier)
            }
        }
    }

    private fun parse(text: String): Map<String, SinnohContent> {
        require(text.toByteArray(Charsets.UTF_8).size <= MAX_BYTES)
        val root = JSONObject(text)
        require(root.getInt("schema") == 1)
        val groups = root.getJSONObject("groups")
        require(groups.keys().asSequence().toSet() == GROUPS)
        return GROUPS.associateWith { group ->
            val value = groups.getJSONObject(group)
            val berries = sinnohRows(value.getJSONArray("berries"), 64).map(::berry)
            val moves = sinnohRows(value.getJSONArray("moves"), 467)
            require(berries.map { it.identifier }.distinct().size == 64)
            require(moves.map { it.getInt("id") }.toSet() == (1..467).toSet())
            SinnohContent(
                berries.associateBy { it.identifier },
                moves.associate { row ->
                    require(row.getInt("effect_id") in 1..23)
                    row.getInt("id") to SuperContestMove(
                        ContestCategory.valueOf(row.getString("category")),
                        row.getInt("appeal"),
                        row.getString("effect")
                    )
                },
                sinnohUnderground(value),
                sinnohBattles(value, group == "platinum")
            )
        }
    }

    private fun berry(row: JSONObject): SinnohBerry {
        require(row.getInt("min_yield") == 2)
        val flavors = row.getJSONArray("flavors")
        require(flavors.length() == 5)
        return SinnohBerry(
            row.getString("identifier"),
            row.getString("name"),
            row.getInt("stage_hours"),
            row.getInt("max_yield"),
            row.getInt("drain_rate"),
            row.getInt("smoothness"),
            List(5) { flavors.getInt(it) }
        )
    }

    private companion object {
        const val MAX_BYTES = 2 * 1024 * 1024
        val GROUPS = setOf("diamond-pearl", "platinum")
    }
}

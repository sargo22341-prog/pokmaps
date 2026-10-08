package org.opensources.pokmaps.data.settings

import org.json.JSONArray
import org.json.JSONObject
import org.opensources.pokmaps.data.json.JsonLimits
import org.opensources.pokmaps.domain.guide.CollectionBackup
import org.opensources.pokmaps.domain.guide.GuideProgress
import org.opensources.pokmaps.domain.guide.RoamerObservation
import org.opensources.pokmaps.domain.pokemon.UnownForm

internal object BackupJson {
    fun encode(backup: CollectionBackup): String {
        val games = JSONArray()
        for (version in 1..6) {
            val progress = backup.guides[version] ?: GuideProgress()
            val roamers = JSONArray(
                progress.roamers.sortedBy { it.pokemonId }.map {
                    JSONObject().put("pokemon", it.pokemonId).put("place", it.place)
                }
            )
            games.put(
                JSONObject().put("version", version)
                    .put("caught", JSONArray(backup.caught[version].orEmpty().sorted()))
                    .put("completed", JSONArray(progress.completed.sorted())).put("roamers", roamers)
                    .put("unown", JSONArray(backup.unown[version].orEmpty().map { it.identifier }.sorted()))
            )
        }
        return JSONObject().put("format", "pokmaps-collection").put("schema", 1)
            .put("favorites", JSONArray(backup.favorites.sorted())).put("games", games).toString(2)
    }

    fun decode(text: String): CollectionBackup {
        JsonLimits.validate(text, MAX_CHARACTERS)
        val json = JSONObject(text)
        require(json.getString("format") == "pokmaps-collection" && integer(json, "schema") == 1)
        val favorites = ids(json.getJSONArray("favorites"))
        val games = json.getJSONArray("games")
        require(games.length() <= 6)
        val caught = mutableMapOf<Int, Set<Int>>()
        val guides = mutableMapOf<Int, GuideProgress>()
        val unown = mutableMapOf<Int, Set<UnownForm>>()
        for (index in 0 until games.length()) {
            val game = games.getJSONObject(index)
            val version = integer(game, "version")
            require(version !in caught)
            caught[version] = ids(game.getJSONArray("caught"))
            val completed = game.getJSONArray("completed")
            require(completed.length() <= 500)
            val articles = (0 until completed.length()).map { completed.getString(it) }.toSet()
            require(articles.size == completed.length())
            val roamers = game.getJSONArray("roamers")
            require(roamers.length() <= 3)
            val observations = (0 until roamers.length()).map {
                val observation = roamers.getJSONObject(it)
                RoamerObservation(integer(observation, "pokemon"), observation.getString("place"))
            }
            guides[version] = GuideProgress(articles, observations)
            val forms = if (game.has("unown")) game.getJSONArray("unown") else JSONArray()
            require(forms.length() <= 26)
            val alphabet = (0 until forms.length()).map { UnownForm.from(forms.getString(it)) }.toSet()
            require(alphabet.size == forms.length())
            if (alphabet.isNotEmpty()) unown[version] = alphabet
        }
        return CollectionBackup(favorites, caught.toMap(), guides.toMap(), unown.toMap())
    }

    private fun ids(array: JSONArray): Set<Int> {
        require(array.length() <= 251)
        val ids = (0 until array.length()).map { requireNotNull(array.get(it) as? Int) }.toSet()
        require(ids.size == array.length())
        return ids
    }

    private fun integer(json: JSONObject, key: String): Int = requireNotNull(json.get(key) as? Int)
    private const val MAX_CHARACTERS = 1_000_000
}

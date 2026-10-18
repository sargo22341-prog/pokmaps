package org.opensources.pokmaps.data.settings

import org.json.JSONArray
import org.json.JSONObject
import org.opensources.pokmaps.data.json.JsonLimits
import org.opensources.pokmaps.domain.guide.CollectionBackup
import org.opensources.pokmaps.domain.guide.GuideProgress
import org.opensources.pokmaps.domain.guide.validateCollectionBackup
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.Generation
import org.opensources.pokmaps.domain.pokemon.UnownForm

internal object BackupJson {
    fun encode(backup: CollectionBackup): String {
        val games = JSONArray()
        for (version in (backup.caught.keys + backup.guides.keys + backup.unown.keys + backup.forms.keys).sorted()) {
            val progress = backup.guides[version] ?: GuideProgress()
            games.put(
                JSONObject().put("version", version)
                    .put("caught", JSONArray(backup.caught[version].orEmpty().sorted()))
                    // Liste vide gardée pour le schéma 1 : les versions précédentes de l'application l'exigent.
                    .put("completed", JSONArray(progress.completed.sorted())).put("roamers", JSONArray())
                    .put("unown", JSONArray(backup.unown[version].orEmpty().map { it.identifier }.sorted()))
                    .put("forms", JSONArray(backup.forms[version].orEmpty().sorted()))
            )
        }
        return JSONObject().put("format", "pokmaps-collection").put("schema", 1)
            .put("favorites", JSONArray(backup.favorites.sorted())).put("games", games).toString(2)
    }

    fun decode(text: String, gamesInDatabase: List<Game>): CollectionBackup {
        JsonLimits.validate(text, MAX_CHARACTERS)
        val json = JSONObject(text)
        require(json.getString("format") == "pokmaps-collection" && integer(json, "schema") == 1)
        val favorites = ids(json.getJSONArray("favorites"))
        val games = json.getJSONArray("games")
        require(games.length() <= gamesInDatabase.size)
        val caught = mutableMapOf<Int, Set<Int>>()
        val guides = mutableMapOf<Int, GuideProgress>()
        val unown = mutableMapOf<Int, Set<UnownForm>>()
        val capturedForms = mutableMapOf<Int, Set<String>>()
        for (index in 0 until games.length()) {
            val game = games.getJSONObject(index)
            val version = integer(game, "version")
            require(version !in caught)
            caught[version] = ids(game.getJSONArray("caught"))
            val completed = game.getJSONArray("completed")
            require(completed.length() <= 500)
            val articles = (0 until completed.length()).map { completed.getString(it) }.toSet()
            require(articles.size == completed.length())
            // Les anciennes observations de Pokémon errants ne sont plus suivies et restent ignorées à l'import.
            require(game.getJSONArray("roamers").length() <= 3)
            guides[version] = GuideProgress(articles)
            val forms = if (game.has("unown")) game.getJSONArray("unown") else JSONArray()
            require(forms.length() <= UnownForm.entries.size)
            val alphabet = (0 until forms.length()).map { UnownForm.from(forms.getString(it)) }.toSet()
            require(alphabet.size == forms.length())
            if (alphabet.isNotEmpty()) unown[version] = alphabet
            val extra = if (game.has("forms")) game.getJSONArray("forms") else JSONArray()
            require(extra.length() <= 200)
            val identifiers = (0 until extra.length()).map { extra.getString(it) }.toSet()
            require(identifiers.size == extra.length())
            if (identifiers.isNotEmpty()) capturedForms[version] = identifiers
        }
        return CollectionBackup(favorites, caught.toMap(), guides.toMap(), unown.toMap(), capturedForms.toMap()).also {
            validateCollectionBackup(it, gamesInDatabase)
        }
    }

    private fun ids(array: JSONArray): Set<Int> {
        require(array.length() <= Generation.maximumSupportedSpecies)
        val ids = (0 until array.length()).map { requireNotNull(array.get(it) as? Int) }.toSet()
        require(ids.size == array.length())
        return ids
    }

    private fun integer(json: JSONObject, key: String): Int = requireNotNull(json.get(key) as? Int)
    private const val MAX_CHARACTERS = 1_000_000
}

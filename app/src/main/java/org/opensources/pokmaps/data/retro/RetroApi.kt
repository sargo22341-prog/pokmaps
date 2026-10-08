package org.opensources.pokmaps.data.retro

import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.SocketTimeoutException
import java.net.URI
import java.net.URLEncoder
import javax.inject.Inject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import org.json.JSONObject
import org.opensources.pokmaps.data.json.JsonLimits
import org.opensources.pokmaps.domain.guide.RetroGames

internal data class RetroUnlocks(val earned: Set<Int>, val hardcore: Set<Int>)

/** Un seul endpoint GET de lecture : aucune méthode de déverrouillage ou d'écriture. */
class RetroApi @Inject constructor() {
    internal suspend fun progress(account: RetroAccount, gameId: Int): RetroUnlocks = withContext(Dispatchers.IO) {
        require(gameId in RetroGames.ids.values)
        val username = URLEncoder.encode(account.username, Charsets.UTF_8.name())
        val address = "$ENDPOINT?y=${account.apiKey}&u=$username&g=$gameId"
        val connection = URI(address).toURL().openConnection() as HttpURLConnection
        try {
            connection.requestMethod = "GET"
            connection.connectTimeout = TIMEOUT_MS
            connection.readTimeout = TIMEOUT_MS
            connection.instanceFollowRedirects = false
            check(connection.responseCode == HttpURLConnection.HTTP_OK) { "Lecture RetroAchievements refusée" }
            require(connection.contentLengthLong <= MAX_BYTES)
            val bytes = readResponse(connection)
            ensureActive()
            parseRetroProgress(String(bytes, Charsets.UTF_8), gameId)
        } finally {
            connection.disconnect()
        }
    }

    private suspend fun readResponse(connection: HttpURLConnection): ByteArray {
        val deadline = System.nanoTime() + TIMEOUT_MS * 1_000_000L
        val buffer = ByteArray(8192)
        val output = ByteArrayOutputStream()
        connection.inputStream.use { input ->
            while (output.size() <= MAX_BYTES) {
                currentCoroutineContext().ensureActive()
                val remaining = deadline - System.nanoTime()
                if (remaining <= 0) throw SocketTimeoutException("Lecture RetroAchievements expirée")
                connection.readTimeout = ((remaining / 1_000_000L).toInt()).coerceIn(1, TIMEOUT_MS)
                val count = input.read(buffer)
                if (count < 0) return output.toByteArray()
                output.write(buffer, 0, count)
            }
        }
        error("Réponse RetroAchievements trop volumineuse")
    }

    private companion object {
        const val ENDPOINT = "https://retroachievements.org/API/API_GetGameInfoAndUserProgress.php"
        const val TIMEOUT_MS = 15_000
        const val MAX_BYTES = 2_000_000
    }
}

internal fun parseRetroProgress(text: String, gameId: Int): RetroUnlocks {
    JsonLimits.validate(text, 2_000_000)
    val json = JSONObject(text)
    require(json.getInt("ID") == gameId)
    val achievements = json.getJSONObject("Achievements")
    require(achievements.length() <= 500)
    val earned = mutableSetOf<Int>()
    val hardcore = mutableSetOf<Int>()
    for (id in achievements.keys()) {
        val achievement = achievements.getJSONObject(id)
        val number = id.toInt().also { require(it > 0 && achievement.getInt("ID") == it) }
        if (hasEarnedDate(achievement, "DateEarned")) earned += number
        if (hasEarnedDate(achievement, "DateEarnedHardcore")) hardcore += number
    }
    return RetroUnlocks(earned + hardcore, hardcore)
}

private fun hasEarnedDate(json: JSONObject, key: String): Boolean {
    if (json.isNull(key)) return false
    val date = requireNotNull(json.get(key) as? String)
    require(date.length in 10..40 && date.take(10).matches(Regex("\\d{4}-\\d{2}-\\d{2}")))
    return true
}

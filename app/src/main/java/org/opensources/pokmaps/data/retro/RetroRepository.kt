package org.opensources.pokmaps.data.retro

import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.emitAll
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.opensources.pokmaps.data.settings.RetroSettings
import org.opensources.pokmaps.domain.guide.RetroGames
import org.opensources.pokmaps.domain.guide.RetroProgress

@Singleton
class RetroRepository @Inject constructor(
    private val credentials: RetroCredentials,
    private val api: RetroApi,
    private val settings: RetroSettings
) {
    private val mutex = Mutex()
    private val username = MutableStateFlow<String?>(null)
    private var initialized = false

    fun observe(): Flow<RetroProgress> = flow {
        mutex.withLock {
            if (!initialized) {
                username.value = credentials.read()?.username
                initialized = true
            }
        }
        emitAll(
            settings.progress.combine(username) { progress, account ->
                if (progress.username == account) progress else RetroProgress(username = account)
            }
        )
    }

    suspend fun connect(name: String, apiKey: String) = mutex.withLock {
        val account = RetroAccount(name.trim(), apiKey.trim())
        credentials.save(account)
        username.value = account.username
        initialized = true
        settings.reset(account.username)
    }

    suspend fun disconnect() = mutex.withLock {
        credentials.delete()
        username.value = null
        initialized = true
        settings.reset(null)
    }

    suspend fun synchronize() = mutex.withLock {
        val account = requireNotNull(credentials.read())
        val earned = mutableMapOf<Int, Set<Int>>()
        val hardcore = mutableMapOf<Int, Set<Int>>()
        for ((version, gameId) in RetroGames.ids) {
            val unlocks = api.progress(account, gameId)
            earned[version] = unlocks.earned
            hardcore[version] = unlocks.hardcore
        }
        settings.save(RetroProgress(account.username, earned.toMap(), hardcore.toMap(), System.currentTimeMillis()))
        username.value = account.username
        initialized = true
    }
}

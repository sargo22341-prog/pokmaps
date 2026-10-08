package org.opensources.pokmaps.domain.usecase

import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import org.opensources.pokmaps.data.retro.RetroRepository
import org.opensources.pokmaps.domain.guide.RetroProgress

interface RetroConnection {
    fun observe(): Flow<RetroProgress>
    suspend fun connect(username: String, apiKey: String)
    suspend fun disconnect()
    suspend fun synchronize()
}

class RetroUseCase @Inject constructor(private val repository: RetroRepository) : RetroConnection {
    override fun observe(): Flow<RetroProgress> = repository.observe()
    override suspend fun connect(username: String, apiKey: String) = repository.connect(username, apiKey)
    override suspend fun disconnect() = repository.disconnect()
    override suspend fun synchronize() = repository.synchronize()
}

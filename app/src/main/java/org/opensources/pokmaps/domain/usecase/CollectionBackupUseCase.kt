package org.opensources.pokmaps.domain.usecase

import javax.inject.Inject
import org.opensources.pokmaps.data.settings.CollectionBackupRepository

interface CollectionDocuments {
    suspend fun export(address: String)
    suspend fun import(address: String)
}

class CollectionBackupUseCase @Inject constructor(private val repository: CollectionBackupRepository) :
    CollectionDocuments {
    override suspend fun export(address: String) = repository.export(address)
    override suspend fun import(address: String) = repository.import(address)
}

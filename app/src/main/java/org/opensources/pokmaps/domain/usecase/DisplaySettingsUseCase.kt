package org.opensources.pokmaps.domain.usecase

import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import org.opensources.pokmaps.data.settings.DisplaySettings

/** Réglages d'affichage des sprites animés : Pokédex et fiches d'un côté, carte de l'autre. */
class DisplaySettingsUseCase @Inject constructor(private val settings: DisplaySettings) {
    val animatedSprites: Flow<Boolean> = settings.animatedSprites

    val mapAnimatedSprites: Flow<Boolean> = settings.mapAnimatedSprites

    suspend fun setAnimatedSprites(enabled: Boolean) = settings.setAnimatedSprites(enabled)

    suspend fun setMapAnimatedSprites(enabled: Boolean) = settings.setMapAnimatedSprites(enabled)
}

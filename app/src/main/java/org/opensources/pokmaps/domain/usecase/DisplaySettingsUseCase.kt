package org.opensources.pokmaps.domain.usecase

import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import org.opensources.pokmaps.data.settings.DisplaySettings
import org.opensources.pokmaps.domain.model.SpritePlace

/** Sprites animés ou fixes, endroit par endroit (carte, liste du lieu, Pokédex, fiches, évolutions…). */
class DisplaySettingsUseCase @Inject constructor(private val settings: DisplaySettings) {
    val animatedPlaces: Flow<Set<SpritePlace>> = settings.animatedPlaces

    suspend fun setAnimated(place: SpritePlace, enabled: Boolean) = settings.setAnimated(setOf(place), enabled)

    /** Anime ou fige les sprites partout. */
    suspend fun setAllAnimated(enabled: Boolean) = settings.setAnimated(SpritePlace.entries.toSet(), enabled)
}

package org.opensources.pokmaps.domain.usecase

import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.repository.MapRepository
import org.opensources.pokmaps.domain.model.GameMap

/** Carte du monde (Kanto) du jeu choisi. */
class ObserveWorldMapUseCase @Inject constructor(private val games: GameRepository, private val maps: MapRepository) {
    operator fun invoke(): Flow<GameMap?> = games.selectedGame.map { maps.map(it, GameMap.WORLD) }
}

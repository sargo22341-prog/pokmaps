package org.opensources.pokmaps.data.repository

import javax.inject.Inject
import javax.inject.Singleton
import org.opensources.pokmaps.data.db.MapDao
import org.opensources.pokmaps.data.db.MapEntity
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.GameMap
import org.opensources.pokmaps.domain.model.MapRegion

@Singleton
class MapRepository @Inject constructor(private val dao: MapDao) {
    /** Carte affichable `identifier` du jeu, avec ses villes et routes pour la carte du monde. */
    suspend fun map(game: Game, identifier: String): GameMap? {
        val entity = dao.map(game.versionGroupId, identifier) ?: return null
        if (entity.parentMapId != null) return null
        return GameMap(
            id = entity.id,
            identifier = entity.identifier,
            name = entity.nameFr,
            versionGroupIdentifier = game.versionGroupIdentifier,
            width = entity.width,
            height = entity.height,
            levelCount = entity.levelCount,
            regions = dao.regions(entity.id).map { it.toRegion() }
        )
    }

    private fun MapEntity.toRegion() = MapRegion(id, identifier, nameFr, x, y, width, height)
}

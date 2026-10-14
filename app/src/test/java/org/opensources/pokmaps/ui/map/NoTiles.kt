package org.opensources.pokmaps.ui.map

import org.opensources.pokmaps.domain.model.GameMap
import ovh.plrapps.mapcompose.core.TileStreamProvider

/** Tuiles absentes : les tests de la carte ne dessinent aucune image. */
internal val noTiles: (GameMap) -> TileStreamProvider = { TileStreamProvider { _, _, _ -> null } }

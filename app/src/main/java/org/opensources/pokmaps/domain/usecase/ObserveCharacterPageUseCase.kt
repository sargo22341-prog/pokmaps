package org.opensources.pokmaps.domain.usecase

import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import org.opensources.pokmaps.data.repository.GameRepository
import org.opensources.pokmaps.data.repository.MapRepository
import org.opensources.pokmaps.domain.map.CharacterRole
import org.opensources.pokmaps.domain.map.FossilUse
import org.opensources.pokmaps.domain.map.MapInfo
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.map.NpcOffer
import org.opensources.pokmaps.domain.map.TrainerPokemon
import org.opensources.pokmaps.domain.map.kind
import org.opensources.pokmaps.domain.model.Game

/** Fiche d'un personnage ou d'un dresseur. */
data class CharacterPage(
    val game: Game,
    val obj: MapObject,
    val map: MapInfo,
    val party: List<TrainerPokemon>,
    val offers: List<NpcOffer>,
    /** Ce que deviennent les fossiles du jeu (pour un personnage qui en donne). */
    val fossilUses: Map<String, FossilUse> = emptyMap()
) {
    val roles: List<CharacterRole> get() = CharacterRole.of(obj.kind, offers.map { it.kind })
}

class ObserveCharacterPageUseCase @Inject constructor(
    private val games: GameRepository,
    private val maps: MapRepository
) {
    /** Fiche du personnage (identifiant propre à la série de cartes du jeu), null s'il n'est pas dans ce jeu. */
    operator fun invoke(objectId: Int): Flow<CharacterPage?> = games.selectedGame.map { game ->
        val catalog = maps.catalog(game)
        val obj = catalog.objectsById[objectId] ?: return@map null
        val map = catalog.maps[obj.mapId] ?: return@map null
        val party = if (obj.kind == MapObjectKind.TRAINER) maps.trainerParty(game, obj.id) else emptyList()
        CharacterPage(game, obj, map, party, maps.offers(game, obj.id), FossilUse.of(maps.index(game), catalog))
    }
}

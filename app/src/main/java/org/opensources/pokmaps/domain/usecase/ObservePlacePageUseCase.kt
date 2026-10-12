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
import org.opensources.pokmaps.domain.map.OfferLink
import org.opensources.pokmaps.domain.map.kind
import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.Game

/** Fiche d'un lieu : Pokémon sauvages, objets, personnages et lieux accessibles. */
data class PlacePage(
    val game: Game,
    val map: MapInfo,
    val encounters: List<Encounter>,
    val items: List<MapObject>,
    /** Dresseurs, Pokémon fixes et personnages qui donnent, vendent ou échangent quelque chose. */
    val characters: List<MapObject>,
    val offers: Map<Int, List<OfferLink>>,
    val places: List<MapInfo>,
    /** Ce que deviennent les fossiles du jeu (pour un personnage du lieu qui en donne). */
    val fossilUses: Map<String, FossilUse> = emptyMap(),
    val outdoor: Boolean = false
) {
    /** Rôles d'un personnage du lieu (dresseur, personnage, ses fonctions). */
    fun rolesOf(obj: MapObject): List<CharacterRole> =
        CharacterRole.of(obj.kind, offers[obj.id].orEmpty().map { it.kind })
}

class ObservePlacePageUseCase @Inject constructor(private val games: GameRepository, private val maps: MapRepository) {
    /** Fiche du lieu dans le jeu choisi (d'après l'identifiant de sa carte), null s'il n'y existe pas. */
    operator fun invoke(identifier: String): Flow<PlacePage?> = games.selectedGame.map { game ->
        val catalog = maps.catalog(game)
        val map = catalog.mapByIdentifier(identifier) ?: return@map null
        val parts = if (map.isDisplayable) catalog.partsOf(map.id) else listOf(map.id)
        val objects = parts.flatMap { catalog.objects[it].orEmpty() }
        val index = maps.index(game)
        val offers = index.offers.groupBy { it.objectId }.filterKeys { id -> objects.any { it.id == id } }
        PlacePage(
            game = game,
            map = map,
            encounters = maps.encounters(
                game,
                parts.flatMap {
                    catalog.areas[it].orEmpty()
                }.map { it.areaId }.distinct()
            ),
            items = objects.filter { it.kind == MapObjectKind.ITEM || it.kind == MapObjectKind.HIDDEN_ITEM },
            characters = objects.filter {
                it.kind == MapObjectKind.TRAINER || it.kind == MapObjectKind.POKEMON || it.id in offers
            },
            offers = offers,
            places = catalog.accessibleFrom(map.id).mapNotNull { warp -> warp.targetMapId?.let { catalog.maps[it] } },
            fossilUses = FossilUse.of(index, catalog),
            outdoor = catalog.displayedMapOf(map.id)?.isWorld == true
        )
    }
}

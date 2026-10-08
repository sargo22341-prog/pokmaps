package org.opensources.pokmaps.ui.map

import org.opensources.pokmaps.domain.map.MapCatalog
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.model.GameMap
import org.opensources.pokmaps.domain.model.groupByMethod
import org.opensources.pokmaps.domain.usecase.GetMapEncountersUseCase
import org.opensources.pokmaps.domain.usecase.GetMapObjectDetailsUseCase

/**
 * Lieu sélectionné sur la carte (ses Pokémon sauvages y sont dessinés) et fiche de l'élément touché
 * (Pokémon sauvage, objet, personnage), chargés en arrière-plan.
 */
internal class MapSelection(
    private val session: MapSession,
    private val getMapEncounters: GetMapEncountersUseCase,
    private val getObjectDetails: GetMapObjectDetailsUseCase
) {
    /** Sélectionne une ville, une route ou une carte intérieure et charge ses rencontres. */
    fun selectZone(catalog: MapCatalog, zoneId: Int) {
        val game = session.loaded.value?.game ?: return
        val info = catalog.maps[zoneId] ?: return
        val items = catalog.objects[zoneId].orEmpty().filter {
            it.kind == MapObjectKind.ITEM || it.kind == MapObjectKind.HIDDEN_ITEM
        }
        val zone = MapZone(
            mapId = zoneId,
            name = info.name,
            places = MapZoneContent.places(catalog, info),
            items = items
        )
        session.updateOverlays { it.copy(wildMarkers = emptyList()) }
        session.update { it.copy(zone = zone, detail = null, zoneListOpen = false) }
        session.refreshOverlays()
        session.load(
            block = { getMapEncounters(game, catalog, zoneId) },
            onFailure = {
                session.update { state ->
                    if (state.zone == zone) state.copy(zone = zone.copy(loading = false, failed = true)) else state
                }
            }
        ) { encounters ->
            if (session.current.zone != zone) return@load
            val wildMarkers = MapZoneContent.wildMarkers(catalog, info, encounters)
            session.updateOverlays { it.copy(wildMarkers = wildMarkers) }
            session.update { it.copy(zone = zone.copy(loading = false, encounters = encounters)) }
            session.refreshOverlays()
        }
    }

    /** Désélectionne la ville ou la route (une carte intérieure reste toujours sélectionnée). */
    fun clearZone() {
        val map = session.current.map
        if (map != null && map.identifier != GameMap.WORLD) return
        session.updateOverlays { it.copy(wildMarkers = emptyList()) }
        session.update { it.copy(zone = null, detail = null, zoneListOpen = false) }
        session.refreshOverlays()
    }

    /** Ouvre la fiche détaillée d'un Pokémon sauvage du lieu sélectionné. */
    fun showWildPokemon(pokemonId: Int) {
        val zone = session.current.zone ?: return
        val encounters = zone.encounters.filter { it.pokemonId == pokemonId }
        val name = encounters.firstOrNull()?.pokemonName ?: return
        session.update { it.copy(detail = MapDetail.WildPokemon(pokemonId, name, encounters.groupByMethod())) }
    }

    fun showObject(obj: MapObject) {
        when (obj.kind) {
            MapObjectKind.ITEM, MapObjectKind.HIDDEN_ITEM -> showItem(obj)

            MapObjectKind.TRAINER, MapObjectKind.NPC, MapObjectKind.NPC_OBJECT, MapObjectKind.NPC_POKEMON,
            MapObjectKind.POKEMON, MapObjectKind.VENDING_MACHINE, MapObjectKind.PRIZE_VENDOR,
            MapObjectKind.HEAL_SPOT -> showCharacter(obj)
        }
    }

    fun dismissDetail() {
        session.update { it.copy(detail = null) }
        if (session.overlays.focusedObjectId != null) {
            session.updateOverlays { it.copy(focusedObjectId = null) }
            session.refreshOverlays()
        }
    }

    private fun showItem(obj: MapObject) {
        val game = session.loaded.value?.game ?: return
        val detail = MapDetail.Item(obj)
        session.update { it.copy(detail = detail, zoneListOpen = false) }
        val itemId = obj.itemId ?: return
        session.load(
            block = { getObjectDetails.item(game, itemId) },
            onFailure = { replaceDetail(detail, detail.copy(failed = true)) }
        ) { details -> replaceDetail(detail, detail.copy(details = details)) }
    }

    /**
     * Dresseur, personnage, Pokémon fixe ou installation : son équipe (dresseur), ce qu'il propose, et ce que
     * deviennent les fossiles qu'il donne.
     */
    private fun showCharacter(obj: MapObject) {
        val loaded = session.loaded.value ?: return
        val game = loaded.game
        val detail = MapDetail.Character(obj)
        session.update { it.copy(detail = detail, zoneListOpen = false) }
        session.load(
            block = {
                val isTrainer = obj.kind == MapObjectKind.TRAINER
                val party = if (isTrainer) getObjectDetails.trainerParty(game, obj.id) else emptyList()
                detail.copy(
                    loading = false,
                    party = party,
                    offers = getObjectDetails.offers(game, obj.id),
                    fossilUses = getObjectDetails.fossilUses(game, loaded.catalog)
                )
            },
            onFailure = { replaceDetail(detail, detail.copy(loading = false, failed = true)) }
        ) { ready -> replaceDetail(detail, ready) }
    }

    /** Remplace la fiche affichée, sauf si l'utilisateur en a ouvert une autre entre-temps. */
    private fun replaceDetail(shown: MapDetail, replacement: MapDetail) {
        session.update { if (it.detail == shown) it.copy(detail = replacement) else it }
    }
}

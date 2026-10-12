package org.opensources.pokmaps.ui.map

import kotlinx.coroutines.Job
import org.opensources.pokmaps.domain.map.MapCatalog
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.TimeFilter
import org.opensources.pokmaps.domain.model.groupByMethod
import org.opensources.pokmaps.domain.model.matchesTimes
import org.opensources.pokmaps.domain.usecase.GameMaps
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
    private var zoneJob: Job? = null
    private var detailJob: Job? = null

    // L'identité du jeton distingue aussi deux demandes identiques A → B → A.
    private var zoneRequest: Any? = null
    private var detailRequest: Any? = null

    fun invalidateLoads() {
        zoneRequest = null
        zoneJob?.cancel()
        cancelDetailLoad()
        loadedEncounters = emptyList()
        loadedZones = emptyMap()
    }

    private var loadedEncounters: List<Encounter> = emptyList()
    private var loadedZones: Map<Int, List<Encounter>> = emptyMap()

    /** Sélectionne une ville, une route ou une carte intérieure et charge ses rencontres. */
    fun selectZone(catalog: MapCatalog, zoneId: Int) {
        val loaded = session.loaded.value ?: return
        val info = catalog.regionsOf(zoneId).firstOrNull()?.takeIf { !catalog.isWorld(zoneId) }
            ?: catalog.maps[zoneId] ?: return
        val selectedId = info.id
        val display = catalog.displayedMapOf(selectedId) ?: return
        val zoneIds = if (display.isWorld) {
            listOf(selectedId)
        } else {
            catalog.regionsOf(display.id).map { it.id }
                .ifEmpty { listOf(selectedId) }
        }
        val items = catalog.objects[selectedId].orEmpty().filter {
            it.kind == MapObjectKind.ITEM || it.kind == MapObjectKind.HIDDEN_ITEM
        }
        invalidateLoads()
        val zone = MapZone(
            mapId = selectedId,
            name = info.name,
            places = MapZoneContent.places(catalog, info),
            items = items
        )
        session.updateOverlays { it.copy(wildMarkers = emptyList()) }
        session.update {
            it.copy(
                zone = zone,
                detail = null,
                zoneListOpen = false,
                floors = if (display.isWorld) catalog.floorsOf(selectedId) else it.floors
            )
        }
        session.refreshOverlays()
        loadZone(loaded, catalog, zone, zoneIds)
    }

    private fun loadZone(loaded: GameMaps, catalog: MapCatalog, zone: MapZone, zoneIds: List<Int>) {
        val request = Any()
        zoneRequest = request
        zoneJob = session.load(
            block = { zoneIds.associateWith { getMapEncounters(loaded.game, catalog, it) } },
            onFailure = {
                if (isCurrent(loaded, request, zoneRequest)) {
                    session.update { it.copy(zone = zone.copy(loading = false, failed = true)) }
                }
            }
        ) { encounters ->
            if (!isCurrent(loaded, request, zoneRequest)) return@load
            loadedZones = encounters
            loadedEncounters = encounters[zone.mapId].orEmpty()
            applyTimes(catalog, zone)
        }
    }

    private fun isCurrent(loaded: GameMaps, request: Any, current: Any?): Boolean =
        session.loaded.value === loaded && current === request

    fun selectTime(time: TimeFilter) {
        cancelDetailLoad()
        session.update { it.copy(time = time, detail = null) }
        val catalog = session.catalog ?: return
        val zone = session.current.zone?.takeIf { !it.loading && !it.failed } ?: return
        applyTimes(catalog, zone)
    }

    private fun applyTimes(catalog: MapCatalog, zone: MapZone) {
        val encounters = loadedEncounters.filter { it.matchesTimes(session.current.times) }
        val markers = loadedZones.flatMap { (id, all) ->
            val info = catalog.maps[id] ?: return@flatMap emptyList()
            MapZoneContent.wildMarkers(catalog, info, all.filter { it.matchesTimes(session.current.times) })
        }
        session.updateOverlays { it.copy(wildMarkers = markers) }
        session.update {
            it.copy(zone = zone.copy(loading = false, encounters = encounters, allEncounters = loadedEncounters))
        }
        session.refreshOverlays()
    }

    /** Désélectionne la ville ou la route (une carte intérieure reste toujours sélectionnée). */
    fun clearZone() {
        val map = session.current.map
        if (map != null && !map.isWorld) return
        invalidateLoads()
        session.updateOverlays { it.copy(wildMarkers = emptyList()) }
        session.update { it.copy(zone = null, detail = null, zoneListOpen = false, floors = emptyList()) }
        session.refreshOverlays()
    }

    /** Ouvre la fiche détaillée d'un Pokémon sauvage du lieu sélectionné. */
    fun showWildPokemon(pokemonId: Int, mapId: Int? = session.current.zone?.mapId) {
        val encounters = loadedZones[mapId].orEmpty()
            .filter { it.pokemonId == pokemonId && it.matchesTimes(session.current.times) }
        val name = encounters.firstOrNull()?.pokemonName ?: return
        cancelDetailLoad()
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
        cancelDetailLoad()
        session.update { it.copy(detail = null) }
        if (session.overlays.focusedObjectId != null) {
            session.updateOverlays { it.copy(focusedObjectId = null) }
            session.refreshOverlays()
        }
    }

    private fun showItem(obj: MapObject) {
        val loaded = session.loaded.value ?: return
        val detail = MapDetail.Item(obj)
        val request = beginDetail()
        session.update { it.copy(detail = detail, zoneListOpen = false) }
        val itemId = obj.itemId ?: return
        detailJob = session.load(
            block = { getObjectDetails.item(loaded.game, itemId) },
            onFailure = { replaceDetail(loaded, request, detail.copy(failed = true)) }
        ) { details -> replaceDetail(loaded, request, detail.copy(details = details)) }
    }

    /**
     * Dresseur, personnage, Pokémon fixe ou installation : son équipe (dresseur), ce qu'il propose, et ce que
     * deviennent les fossiles qu'il donne.
     */
    private fun showCharacter(obj: MapObject) {
        val loaded = session.loaded.value ?: return
        val game = loaded.game
        val detail = MapDetail.Character(obj)
        val request = beginDetail()
        session.update { it.copy(detail = detail, zoneListOpen = false) }
        detailJob = session.load(
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
            onFailure = { replaceDetail(loaded, request, detail.copy(loading = false, failed = true)) }
        ) { ready -> replaceDetail(loaded, request, ready) }
    }

    private fun cancelDetailLoad() {
        detailRequest = null
        detailJob?.cancel()
    }

    private fun beginDetail(): Any {
        cancelDetailLoad()
        return Any().also { detailRequest = it }
    }

    /** Seule la demande active dans le catalogue courant peut remplacer la fiche. */
    private fun replaceDetail(loaded: GameMaps, request: Any, replacement: MapDetail) {
        if (isCurrent(loaded, request, detailRequest)) session.update { it.copy(detail = replacement) }
    }
}

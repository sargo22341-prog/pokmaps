package org.opensources.pokmaps.ui.map

import org.opensources.pokmaps.domain.map.CharacterRole
import org.opensources.pokmaps.domain.map.FossilUse
import org.opensources.pokmaps.domain.map.ItemDetails
import org.opensources.pokmaps.domain.map.MapFloor
import org.opensources.pokmaps.domain.map.MapLayer
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.map.NpcOffer
import org.opensources.pokmaps.domain.map.TrainerPokemon
import org.opensources.pokmaps.domain.map.kind
import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.EncounterFilter
import org.opensources.pokmaps.domain.model.EncounterGroup
import org.opensources.pokmaps.domain.model.EncounterTime
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.GameMap
import org.opensources.pokmaps.domain.model.ObtainMethod
import org.opensources.pokmaps.domain.model.TimeFilter
import org.opensources.pokmaps.domain.model.groupByMethod
import org.opensources.pokmaps.domain.model.matchesTimes
import org.opensources.pokmaps.domain.model.wildPokemonIds
import ovh.plrapps.mapcompose.ui.state.MapState

/** Lieu vers lequel on peut aller : carte (ou ville, route) et point d'arrivée, en pixels de la carte affichée. */
data class MapPlace(val mapId: Int, val name: String, val x: Int? = null, val y: Int? = null)

/** Façon de rencontrer un Pokémon sauvage, qui décide où le dessiner sur la carte. */
enum class WildMethod {
    /** Herbes hautes, ou sol des grottes et bâtiments. */
    WALK,
    SURF,
    FISHING,
    HEADBUTT,
    ROCK_SMASH;

    companion object {
        /** Méthode de rencontre PokéAPI ; null pour un Pokémon qu'on ne croise pas à l'état sauvage. */
        fun from(method: String): WildMethod? = when (ObtainMethod.fromEncounterMethod(method)) {
            ObtainMethod.WALK -> WALK
            ObtainMethod.SURF -> SURF
            ObtainMethod.FISHING -> FISHING
            ObtainMethod.HEADBUTT -> HEADBUTT
            ObtainMethod.ROCK_SMASH -> ROCK_SMASH
            ObtainMethod.GIFT, ObtainMethod.STATIC, ObtainMethod.TRADE, ObtainMethod.EVOLUTION -> null
        }
    }
}

/** Pokémon sauvage dessiné sur la carte, à un emplacement de son terrain (en pixels de la carte affichée). */
data class WildMarker(
    val pokemonId: Int,
    val name: String,
    val method: WildMethod,
    val x: Int,
    val y: Int,
    val scale: Float = 1f
)

/**
 * Lieu sélectionné (ville, route ou carte intérieure) : son contenu est dessiné sur la carte
 * (Pokémon sauvages, objets, personnages), la liste détaillée s'ouvre à la demande.
 */
data class MapZone(
    val mapId: Int,
    val name: String,
    val places: List<MapPlace>,
    val items: List<MapObject> = emptyList(),
    val loading: Boolean = true,
    val encounters: List<Encounter> = emptyList(),
    val allEncounters: List<Encounter> = encounters,
    val failed: Boolean = false
) {
    fun availableMethods(time: TimeFilter = TimeFilter.ALL): List<EncounterFilter> {
        if (loading || failed) return emptyList()
        val available = allEncounters.filter { it.matchesTimes(time.times) }
        return EncounterFilter.entries.filter { method -> available.any { method.matches(it) } }
    }

    val groups: List<EncounterGroup> get() = encounters.groupByMethod()

    /** Pokémon sauvages du lieu (herbes, grottes, surf, pêche). */
    val wildIds: Set<Int> get() = encounters.wildPokemonIds()
}

/** Élément touché sur la carte, détaillé dans la carte en bas d'écran. */
sealed interface MapDetail {
    data class WildPokemon(val pokemonId: Int, val name: String, val encounters: List<EncounterGroup>) : MapDetail

    data class Item(val obj: MapObject, val details: ItemDetails? = null, val failed: Boolean = false) : MapDetail

    /**
     * Dresseur, personnage, Pokémon fixe ou installation ; `loading` tant que l'équipe et les offres ne sont pas
     * lues. `fossilUses` : ce que deviennent les fossiles du jeu, pour un personnage qui en donne.
     */
    data class Character(
        val obj: MapObject,
        val loading: Boolean = true,
        val party: List<TrainerPokemon> = emptyList(),
        val offers: List<NpcOffer> = emptyList(),
        val fossilUses: Map<String, FossilUse> = emptyMap(),
        val failed: Boolean = false
    ) : MapDetail {
        val roles: List<CharacterRole> get() = CharacterRole.of(obj.kind, offers.map { it.kind })
    }
}

/** Message ponctuel affiché en bas de la carte. */
sealed interface MapMessage {
    /** Pokémon introuvable sur les cartes de la version. */
    data class NotFound(val pokemonName: String) : MapMessage

    /** Les lieux du Pokémon n'ont pas pu être lus. */
    data class HighlightFailed(val pokemonName: String) : MapMessage
}

/** Mode « surlignage » : lieux d'un Pokémon dans la version choisie. */
data class MapHighlight(val pokemonId: Int, val name: String, val places: List<MapPlace>)

data class MapUiState(
    val game: Game? = null,
    val worlds: List<MapPlace> = emptyList(),
    val worldId: Int? = null,
    val time: TimeFilter = TimeFilter.ALL,
    val map: GameMap? = null,
    val mapState: MapState? = null,
    /** Niveau du dessus (bâtiment, ville ou route qui contient la carte intérieure), pour le bouton retour. */
    val parent: MapPlace? = null,
    /** Étages du bâtiment ou de la grotte affiché, de haut en bas (vide s'il n'a qu'un niveau). */
    val floors: List<MapFloor> = emptyList(),
    val layers: Set<MapLayer> = MapLayer.entries.toSet(),
    /** Pokémon capturés dans la version. */
    val caught: Set<Int> = emptySet(),
    val zone: MapZone? = null,
    val detail: MapDetail? = null,
    /** Liste détaillée du lieu sélectionné ouverte. */
    val zoneListOpen: Boolean = false,
    val highlight: MapHighlight? = null,
    /** Message à afficher une fois (voir [MapAction.MessageShown]). */
    val message: MapMessage? = null,
    val failed: Boolean = false
) {
    val times: Set<EncounterTime> get() = time.times
}

/** Intentions de l'écran de la carte, traitées par [MapViewModel]. */
sealed interface MapAction {
    /** Remonte d'un niveau, ou désélectionne le lieu sur la carte du monde. */
    data object Back : MapAction

    data class OpenPlace(val place: MapPlace) : MapAction

    data class SelectWorld(val mapId: Int) : MapAction

    data object CycleTime : MapAction

    data class SelectFloor(val mapId: Int) : MapAction

    data class ToggleLayer(val layer: MapLayer) : MapAction

    data object ClearHighlight : MapAction

    data object ClearZone : MapAction

    data object OpenZoneList : MapAction

    data object CloseZoneList : MapAction

    data object DismissDetail : MapAction

    /** Montre un objet ou un personnage, dans sa carte (ex. le scientifique qui ranime un fossile). */
    data class FocusObject(val objectId: Int) : MapAction

    /** Le message de [MapUiState.message] a été affiché. */
    data object MessageShown : MapAction
}

internal object MapMarkerIds {
    const val LAZY_LOADER = "lazy"
    const val WARP = "w"
    const val OBJECT = "o"
    const val WILD = "p"
    const val HIGHLIGHT_WARP = "hw"
    const val HIGHLIGHT_OBJECT = "ho"
    const val HIGHLIGHT_PATH = "hp"
    const val ZONE_PATH = "zp"
}

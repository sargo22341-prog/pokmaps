package org.opensources.pokmaps.ui.map

import org.opensources.pokmaps.domain.map.ItemDetails
import org.opensources.pokmaps.domain.map.MapFloor
import org.opensources.pokmaps.domain.map.MapLayer
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.map.NpcOffer
import org.opensources.pokmaps.domain.map.TrainerPokemon
import org.opensources.pokmaps.domain.model.Encounter
import org.opensources.pokmaps.domain.model.EncounterGroup
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.GameMap
import org.opensources.pokmaps.domain.model.groupByMethod
import ovh.plrapps.mapcompose.ui.state.MapState

/** Lieu vers lequel on peut aller : carte (ou ville, route) et point d'arrivée, en pixels de la carte affichée. */
data class MapPlace(val mapId: Int, val name: String, val x: Int? = null, val y: Int? = null)

/** Façon de rencontrer un Pokémon sauvage, qui décide où le dessiner sur la carte. */
enum class WildMethod {
    /** Herbes hautes, ou sol des grottes et bâtiments. */
    WALK,
    SURF,
    FISHING;

    companion object {
        fun from(method: String): WildMethod? = when (method) {
            "walk" -> WALK
            "surf" -> SURF
            "old-rod", "good-rod", "super-rod" -> FISHING
            else -> null
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
    val loading: Boolean = true,
    val encounters: List<Encounter> = emptyList()
) {
    val groups: List<EncounterGroup> get() = encounters.groupByMethod()

    /** Pokémon sauvages du lieu (herbes, grottes, surf, pêche). */
    val wildIds: Set<Int> get() = encounters.filter { WildMethod.from(it.method) != null }.map { it.pokemonId }.toSet()
}

/** Élément touché sur la carte, détaillé dans la carte en bas d'écran. */
sealed interface MapDetail {
    data class WildPokemon(val pokemonId: Int, val name: String, val encounters: List<EncounterGroup>) : MapDetail

    data class Item(val obj: MapObject, val details: ItemDetails? = null) : MapDetail

    /** Dresseur, personnage ou Pokémon fixe ; `loading` tant que l'équipe et les offres ne sont pas lues. */
    data class Character(
        val obj: MapObject,
        val loading: Boolean = true,
        val party: List<TrainerPokemon> = emptyList(),
        val offers: List<NpcOffer> = emptyList()
    ) : MapDetail
}

/** Mode « surlignage » : lieux d'un Pokémon dans la version choisie. */
data class MapHighlight(val pokemonId: Int, val name: String, val places: List<MapPlace>)

data class MapUiState(
    val game: Game? = null,
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
    /** Pokémon introuvable sur les cartes de la version (message à afficher une fois). */
    val notFound: String? = null,
    /** Sprites animés sur la carte et dans la liste du lieu (réglage). */
    val animatedSprites: Boolean = false
)

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

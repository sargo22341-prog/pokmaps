package org.opensources.pokmaps.ui.map

import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import org.opensources.pokmaps.domain.map.MapObject
import ovh.plrapps.mapcompose.ui.state.MapState

/** Ce que dessine un marqueur. Toutes ses données y figurent : deux contenus égaux dessinent la même chose. */
internal sealed interface MarkerContent {
    data class Warp(val alwaysVisible: Boolean, val color: Color) : MarkerContent

    /** Accès à l'île superposée, ou retour à la route (`returnTo`, nom de la route) quand elle est affichée. */
    data class MirageIsland(val alwaysVisible: Boolean, val returnTo: String?) : MarkerContent

    data class SecretBase(val alwaysVisible: Boolean) : MarkerContent

    /** Objet, dresseur, personnage, Pokémon fixe ou installation. */
    data class Element(
        val obj: MapObject,
        val versionGroupIdentifier: String,
        val alwaysVisible: Boolean,
        val scale: Float
    ) : MarkerContent

    data class Wild(val wild: WildMarker) : MarkerContent

    data class Battle(val alwaysVisible: Boolean) : MarkerContent

    data object Highlight : MarkerContent
}

/** Marqueur à dessiner sur la carte affichée, en pixels de la carte. */
internal data class MarkerSpec(
    val x: Int,
    val y: Int,
    val lazy: Boolean,
    val zIndex: Float,
    val pokemon: Boolean,
    val content: MarkerContent
)

@Composable
internal fun MarkerContent.Draw(mapState: MapState) {
    when (this) {
        is MarkerContent.Warp -> WarpMarker(mapState, alwaysVisible = alwaysVisible, color = color)

        is MarkerContent.MirageIsland -> MirageIslandMarker(
            mapState,
            alwaysVisible = alwaysVisible,
            returnTo = returnTo
        )

        is MarkerContent.SecretBase -> SecretBaseMarker(mapState, alwaysVisible = alwaysVisible)

        is MarkerContent.Element -> ObjectMarker(mapState, obj, versionGroupIdentifier, alwaysVisible, scale)

        is MarkerContent.Wild -> WildPokemonMarker(mapState, wild)

        is MarkerContent.Battle -> BattleMarker(mapState, alwaysVisible)

        MarkerContent.Highlight -> HighlightMarker()
    }
}

/** Marqueurs à retirer de la carte, puis à y ajouter (dans l'ordre), pour passer de `drawn` à `wanted`. */
internal data class MarkerUpdates(val removed: List<String>, val added: List<String>)

/**
 * Seuls les marqueurs nouveaux, disparus ou modifiés changent : MapCompose recopie sa liste et la parcourt à
 * chaque ajout, si bien que tout redessiner coûtait un temps quadratique en nombre de marqueurs.
 *
 * À zIndex égal, MapCompose dessine les marqueurs dans leur ordre d'ajout. Les Pokémon sauvages, ajoutés après les
 * objets lors d'un rendu complet, sont donc rajoutés dès qu'un objet l'est, pour rester dessinés au-dessus.
 */
internal fun markerUpdates(drawn: Map<String, MarkerSpec>, wanted: Map<String, MarkerSpec>): MarkerUpdates {
    var elementAdded = false
    val added = buildList {
        for ((id, spec) in wanted) {
            val reorder = elementAdded && spec.content is MarkerContent.Wild
            if (drawn[id] == spec && !reorder) continue
            add(id)
            if (spec.content is MarkerContent.Element) elementAdded = true
        }
    }
    val replaced = added.toSet()
    return MarkerUpdates(drawn.keys.filter { it !in wanted || it in replaced }, added)
}

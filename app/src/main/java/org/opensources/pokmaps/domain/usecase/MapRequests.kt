package org.opensources.pokmaps.domain.usecase

import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/** Demande d'affichage sur la carte, venue d'un autre écran (boutons « Voir sur la carte » des fiches). */
sealed interface MapRequest {
    data class HighlightPokemon(val pokemonId: Int, val name: String) : MapRequest

    /** Ouvre un lieu (ville, route ou carte intérieure), d'après l'identifiant de sa carte. */
    data class OpenPlace(val mapIdentifier: String) : MapRequest

    /** Centre la carte sur un objet ou un personnage (en entrant dans son bâtiment) et ouvre sa fiche. */
    data class FocusObject(val objectId: Int) : MapRequest
}

/** Transmet les demandes à l'écran de la carte, qui les consomme. */
@Singleton
class MapRequests @Inject constructor() {
    private val _pending = MutableStateFlow<MapRequest?>(null)
    val pending: StateFlow<MapRequest?> = _pending.asStateFlow()

    fun send(request: MapRequest) {
        _pending.value = request
    }

    fun consume(request: MapRequest) {
        _pending.compareAndSet(request, null)
    }
}

package org.opensources.pokmaps.domain.usecase

import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/** Demande d'affichage sur la carte, venue d'un autre écran (bouton « Voir sur la carte » de la fiche Pokémon). */
sealed interface MapRequest {
    data class HighlightPokemon(val pokemonId: Int, val name: String) : MapRequest
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

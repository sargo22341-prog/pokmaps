package org.opensources.pokmaps.ui.place

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import org.opensources.pokmaps.domain.model.EncounterGroup
import org.opensources.pokmaps.domain.model.groupByMethod
import org.opensources.pokmaps.domain.model.wildPokemonIds
import org.opensources.pokmaps.domain.usecase.MapRequest
import org.opensources.pokmaps.domain.usecase.MapRequests
import org.opensources.pokmaps.domain.usecase.ObserveCollectionUseCase
import org.opensources.pokmaps.domain.usecase.ObservePlacePageUseCase
import org.opensources.pokmaps.domain.usecase.PlacePage
import org.opensources.pokmaps.ui.common.STOP_TIMEOUT_MS

data class PlaceUiState(
    val loading: Boolean = true,
    val page: PlacePage? = null,
    /** Pokémon capturés dans la version du jeu. */
    val caught: Set<Int> = emptySet(),
    val failed: Boolean = false
) {
    /** Pokémon du lieu, groupés par méthode de rencontre. */
    val encounterGroups: List<EncounterGroup> = page?.encounters.orEmpty().groupByMethod()

    /** Pokémon sauvages du lieu (herbes, grottes, surf, pêche) : le lieu est terminé quand tous sont capturés. */
    val wildIds: Set<Int> = page?.encounters.orEmpty().wildPokemonIds()

    val caughtWild: Int = wildIds.count { it in caught }
}

/** Intentions de la fiche d'un lieu. */
sealed interface PlaceAction {
    /** Montre le lieu sur la carte. */
    data object ShowPlace : PlaceAction

    /** Montre sur la carte un objet ou un personnage du lieu. */
    data class ShowObject(val objectId: Int) : PlaceAction
}

/** Fiche d'un lieu (ville, route ou carte intérieure) du jeu choisi. */
@HiltViewModel
class PlaceViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    observePlace: ObservePlacePageUseCase,
    observeCollection: ObserveCollectionUseCase,
    private val mapRequests: MapRequests
) : ViewModel() {
    private val identifier: String = checkNotNull(savedStateHandle[PLACE])

    val state: StateFlow<PlaceUiState> = combine(observePlace(identifier), observeCollection()) { page, collection ->
        PlaceUiState(loading = false, page = page, caught = collection.caught)
    }
        .catch { emit(PlaceUiState(loading = false, failed = true)) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(STOP_TIMEOUT_MS), PlaceUiState())

    fun onAction(action: PlaceAction) {
        when (action) {
            PlaceAction.ShowPlace -> mapRequests.send(MapRequest.OpenPlace(identifier))
            is PlaceAction.ShowObject -> mapRequests.send(MapRequest.FocusObject(action.objectId))
        }
    }

    companion object {
        const val PLACE = "place"
    }
}

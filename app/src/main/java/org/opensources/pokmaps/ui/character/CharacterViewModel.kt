package org.opensources.pokmaps.ui.character

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import org.opensources.pokmaps.domain.map.RivalChoice
import org.opensources.pokmaps.domain.map.TeamSelection
import org.opensources.pokmaps.domain.usecase.CharacterPage
import org.opensources.pokmaps.domain.usecase.MapRequest
import org.opensources.pokmaps.domain.usecase.MapRequests
import org.opensources.pokmaps.domain.usecase.ObserveCharacterPageUseCase
import org.opensources.pokmaps.domain.usecase.RivalChoiceUseCase
import org.opensources.pokmaps.ui.common.STOP_TIMEOUT_MS

data class CharacterUiState(
    val loading: Boolean = true,
    val page: CharacterPage? = null,
    val failed: Boolean = false,
    val rivalChoice: RivalChoice = RivalChoice(),
    /** Le choix du Pokémon de départ ou des combats n'a pas pu être enregistré. */
    val choiceFailed: Boolean = false
) {
    /** Équipes du dresseur, selon la partie indiquée. */
    val teams: TeamSelection = TeamSelection.of(page?.teams.orEmpty(), rivalChoice)
}

/** Intentions de la fiche d'un personnage. */
sealed interface CharacterAction {
    /** Montre le personnage sur la carte, dans son bâtiment. */
    data object ShowOnMap : CharacterAction

    /** Montre un autre personnage sur la carte (ex. le scientifique qui ranime le fossile donné). */
    data class ShowObject(val objectId: Int) : CharacterAction

    /** Change le Pokémon de départ ou l'issue des combats qui fixent l'équipe du rival. */
    data class ChooseRival(val choice: RivalChoice) : CharacterAction
}

/** Fiche d'un personnage ou d'un dresseur. */
@HiltViewModel
class CharacterViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    observeCharacter: ObserveCharacterPageUseCase,
    private val rivalChoice: RivalChoiceUseCase,
    private val mapRequests: MapRequests
) : ViewModel() {
    private val objectId: Int = checkNotNull(savedStateHandle[CHARACTER])
    private val choiceFailed = MutableStateFlow(false)

    val state: StateFlow<CharacterUiState> =
        combine(observeCharacter(objectId), rivalChoice(), choiceFailed) { page, choice, failed ->
            CharacterUiState(loading = false, page = page, rivalChoice = choice, choiceFailed = failed)
        }
            .catch { emit(CharacterUiState(loading = false, failed = true)) }
            .stateIn(viewModelScope, SharingStarted.WhileSubscribed(STOP_TIMEOUT_MS), CharacterUiState())

    fun onAction(action: CharacterAction) {
        when (action) {
            CharacterAction.ShowOnMap -> mapRequests.send(MapRequest.FocusObject(objectId))
            is CharacterAction.ShowObject -> mapRequests.send(MapRequest.FocusObject(action.objectId))
            is CharacterAction.ChooseRival -> chooseRival(action.choice)
        }
    }

    private fun chooseRival(choice: RivalChoice) {
        val game = state.value.page?.game ?: return
        viewModelScope.launch {
            choiceFailed.value = try {
                rivalChoice.set(game, choice)
                false
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (_: Exception) {
                true
            }
        }
    }

    companion object {
        const val CHARACTER = "character"
    }
}

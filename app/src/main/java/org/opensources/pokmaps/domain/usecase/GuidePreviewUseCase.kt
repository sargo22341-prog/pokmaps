package org.opensources.pokmaps.domain.usecase

import javax.inject.Inject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.withContext
import org.opensources.pokmaps.domain.guide.GuideTarget
import org.opensources.pokmaps.domain.model.groupByMethod

sealed interface GuidePreview {
    data class Pokemon(val page: PokemonPage) : GuidePreview
    data class Place(val page: PlacePage) : GuidePreview {
        val encounters = page.encounters.groupByMethod()
    }
    data class Item(val page: ItemPage) : GuidePreview
    data class Character(val page: CharacterPage) : GuidePreview
}

class GuidePreviewUseCase @Inject constructor(
    private val pokemon: ObservePokemonUseCase,
    private val places: ObservePlacePageUseCase,
    private val items: ObserveItemPageUseCase,
    private val characters: ObserveCharacterPageUseCase
) {
    suspend operator fun invoke(target: GuideTarget): GuidePreview? = withContext(Dispatchers.IO) {
        when (target) {
            is GuideTarget.Pokemon -> pokemon(target.id).first().takeIf { it.details != null }?.let {
                GuidePreview.Pokemon(it)
            }

            is GuideTarget.Place -> places(target.identifier).first()?.let { GuidePreview.Place(it) }

            is GuideTarget.Item -> items(target.identifier).first()?.let { GuidePreview.Item(it) }

            is GuideTarget.Character -> characters(target.id).first()?.let { GuidePreview.Character(it) }
        }
    }
}

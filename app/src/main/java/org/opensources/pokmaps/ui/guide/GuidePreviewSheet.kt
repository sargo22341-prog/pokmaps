package org.opensources.pokmaps.ui.guide

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.GuideTarget
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.domain.usecase.GuidePreview
import org.opensources.pokmaps.ui.common.CharacterSprite
import org.opensources.pokmaps.ui.common.EncounterGroups
import org.opensources.pokmaps.ui.common.Offers
import org.opensources.pokmaps.ui.common.PixelArt
import org.opensources.pokmaps.ui.common.PixelArtImage
import org.opensources.pokmaps.ui.common.PokemonSprite
import org.opensources.pokmaps.ui.common.SheetPlaceholder
import org.opensources.pokmaps.ui.common.SpriteSize
import org.opensources.pokmaps.ui.common.TrainerPokemonRow

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun GuidePreviewSheet(state: GuideUiState, onAction: (GuideAction) -> Unit, links: GuideLinks) {
    ModalBottomSheet(onDismissRequest = { onAction(GuideAction.ClosePreview) }) {
        Column(
            Modifier.fillMaxWidth().heightIn(max = 540.dp).verticalScroll(rememberScrollState()).padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            val preview = state.preview
            if (preview == null) {
                SheetPlaceholder(
                    state.previewLoading,
                    stringResource(R.string.guide_preview_empty),
                    failed = state.previewFailed
                )
            } else {
                when (preview) {
                    is GuidePreview.Pokemon -> PokemonPreview(preview)
                    is GuidePreview.Place -> PlacePreview(preview, onAction)
                    is GuidePreview.Item -> ItemPreview(preview)
                    is GuidePreview.Character -> CharacterPreview(preview, onAction)
                }
                state.previewTarget?.let { target ->
                    Button(onClick = {
                        onAction(GuideAction.ClosePreview)
                        links.open(target)
                    }) {
                        Text(stringResource(R.string.guide_open_details))
                    }
                }
            }
            TextButton(onClick = { onAction(GuideAction.ClosePreview) }) { Text(stringResource(R.string.map_close)) }
        }
    }
}

@Composable
private fun PokemonPreview(preview: GuidePreview.Pokemon) {
    val pokemon = preview.page.details ?: return
    PokemonSprite(pokemon.id, SpritePlace.POKEMON_SHEET, SpriteSize.SHEET, pokemon.name)
    Text(pokemon.name, style = MaterialTheme.typography.headlineSmall)
    pokemon.description?.let { Text(it) }
    pokemon.stats.forEach { stat -> Text(stringResource(R.string.guide_stat, stat.name, stat.value)) }
}

@Composable
private fun PlacePreview(preview: GuidePreview.Place, onAction: (GuideAction) -> Unit) {
    Text(preview.page.map.name, style = MaterialTheme.typography.headlineSmall)
    Button(onClick = { onAction(GuideAction.ShowPlace(preview.page.map.identifier)) }) {
        Text(stringResource(R.string.show_on_map))
    }
    if (preview.encounters.isEmpty()) Text(stringResource(R.string.map_no_encounter))
    EncounterGroups(
        preview.encounters,
        title = { it.pokemonName },
        spritePlace = SpritePlace.SHEETS,
        onClick = { onAction(GuideAction.Preview(GuideTarget.Pokemon(it.pokemonId))) }
    )
}

@Composable
private fun ItemPreview(preview: GuidePreview.Item) {
    val item = preview.page.item
    if (item.hasSprite) PixelArtImage(Sprites.item(item.identifier), PixelArt.ITEM_ICON, 48.dp, item.name)
    Text(item.name, style = MaterialTheme.typography.headlineSmall)
    preview.page.details?.description?.let { Text(it) }
    preview.page.details?.move?.let { Text(it.name, style = MaterialTheme.typography.titleMedium) }
}

@Composable
private fun CharacterPreview(preview: GuidePreview.Character, onAction: (GuideAction) -> Unit) {
    val page = preview.page
    CharacterSprite(page.obj, page.game.versionGroupIdentifier)
    Text(page.obj.name, style = MaterialTheme.typography.headlineSmall)
    Text(page.map.name)
    Button(onClick = { onAction(GuideAction.ShowObject(page.obj.id)) }) { Text(stringResource(R.string.show_on_map)) }
    page.party.forEach { pokemon ->
        TrainerPokemonRow(pokemon, SpritePlace.SHEETS) { onAction(GuideAction.Preview(GuideTarget.Pokemon(it))) }
    }
    Offers(
        page.offers,
        SpritePlace.SHEETS,
        page.fossilUses,
        onOpenPokemon = { onAction(GuideAction.Preview(GuideTarget.Pokemon(it))) },
        onOpenItem = { onAction(GuideAction.Preview(GuideTarget.Item(it))) },
        onShowObject = { onAction(GuideAction.ShowObject(it)) }
    )
}

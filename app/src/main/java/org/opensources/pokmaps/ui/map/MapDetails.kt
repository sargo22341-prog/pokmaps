package org.opensources.pokmaps.ui.map

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.map.CharacterRole
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.ui.common.CharacterSprite
import org.opensources.pokmaps.ui.common.EncounterGroups
import org.opensources.pokmaps.ui.common.MoveLine
import org.opensources.pokmaps.ui.common.Offers
import org.opensources.pokmaps.ui.common.PixelArt
import org.opensources.pokmaps.ui.common.PixelArtImage
import org.opensources.pokmaps.ui.common.PokemonSprite
import org.opensources.pokmaps.ui.common.RoleIcons
import org.opensources.pokmaps.ui.common.SectionTitle
import org.opensources.pokmaps.ui.common.SpriteSize
import org.opensources.pokmaps.ui.common.TrainerPokemonRow

/** Fiche de l'élément touché sur la carte, en bas d'écran (la carte reste utilisable). */
@Composable
internal fun DetailCard(
    detail: MapDetail,
    versionGroupIdentifier: String,
    onClose: () -> Unit,
    onOpenPokemon: (Int) -> Unit,
    onOpenItem: (String) -> Unit,
    onShowObject: (Int) -> Unit
) {
    Surface(
        shape = MaterialTheme.shapes.large,
        tonalElevation = 3.dp,
        shadowElevation = 4.dp,
        modifier = Modifier
            .fillMaxWidth()
            .padding(8.dp)
    ) {
        Box {
            Column(
                verticalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier
                    .heightIn(max = DETAIL_MAX_HEIGHT)
                    .verticalScroll(rememberScrollState())
                    .padding(16.dp)
            ) {
                when (detail) {
                    is MapDetail.WildPokemon -> WildPokemonDetails(detail, onOpenPokemon)

                    is MapDetail.Item -> ItemDetailsContent(detail, versionGroupIdentifier, onOpenItem)

                    is MapDetail.Character -> CharacterDetails(
                        detail,
                        versionGroupIdentifier,
                        DetailLinks(onOpenPokemon, onOpenItem, onShowObject)
                    )
                }
            }
            IconButton(onClick = onClose, modifier = Modifier.align(Alignment.TopEnd)) {
                Icon(painterResource(R.drawable.ic_close), stringResource(R.string.map_close))
            }
        }
    }
}

/** Fiches et carte ouvertes depuis la fiche d'un personnage. */
private data class DetailLinks(
    val onOpenPokemon: (Int) -> Unit,
    val onOpenItem: (String) -> Unit,
    val onShowObject: (Int) -> Unit
)

/** En-tête d'une fiche : image, icônes de ce qu'est l'élément (dresseur, personnage…), petite ligne et nom. */
@Composable
private fun DetailHeader(
    label: String,
    title: String,
    roles: List<CharacterRole> = emptyList(),
    content: @Composable () -> Unit
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        modifier = Modifier.padding(end = 40.dp)
    ) {
        content()
        Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
            RoleIcons(roles, size = 24.dp)
            if (label.isNotEmpty()) {
                Text(
                    label,
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            Text(title, style = MaterialTheme.typography.titleLarge)
        }
    }
}

@Composable
private fun WildPokemonDetails(detail: MapDetail.WildPokemon, onOpenPokemon: (Int) -> Unit) {
    DetailHeader(stringResource(R.string.map_wild_pokemon), detail.name) {
        PokemonSprite(detail.pokemonId, SpritePlace.MAP_LIST, SpriteSize.SHEET, contentDescription = null)
    }
    EncounterGroups(detail.encounters, title = { it.areaName })
    Button(onClick = { onOpenPokemon(detail.pokemonId) }) {
        Text(stringResource(R.string.map_open_pokemon, detail.name))
    }
}

@Composable
private fun ItemDetailsContent(detail: MapDetail.Item, versionGroupIdentifier: String, onOpenItem: (String) -> Unit) {
    val obj = detail.obj
    val hidden = obj.kind == MapObjectKind.HIDDEN_ITEM
    DetailHeader(
        stringResource(if (hidden) R.string.map_hidden_item else R.string.map_item),
        obj.itemName.orEmpty()
    ) {
        val identifier = obj.itemIdentifier
        val sprite = obj.sprite
        when {
            identifier != null && obj.itemHasSprite ->
                PixelArtImage(Sprites.item(identifier), PixelArt.ITEM_ICON, 48.dp, null)

            sprite != null -> PixelArtImage(
                Sprites.mapSprite(versionGroupIdentifier, sprite),
                PixelArt.MAP_SPRITE,
                48.dp,
                null
            )
        }
    }
    if (hidden) {
        Text(
            stringResource(R.string.map_hidden_item_hint),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
    if (detail.failed) {
        Text(stringResource(R.string.data_load_error), color = MaterialTheme.colorScheme.error)
        return
    }
    val details = detail.details ?: return
    details.move?.let { move ->
        Text(stringResource(R.string.map_machine_move, move.name), style = MaterialTheme.typography.titleSmall)
        MoveLine(move)
    }
    details.description?.let { Text(it, style = MaterialTheme.typography.bodyMedium) }
    Button(onClick = { onOpenItem(details.identifier) }) {
        Text(stringResource(R.string.map_open_item, details.name))
    }
}

@Composable
private fun CharacterDetails(detail: MapDetail.Character, versionGroupIdentifier: String, links: DetailLinks) {
    val obj = detail.obj
    val pokemonId = obj.pokemonId
    if (obj.kind == MapObjectKind.POKEMON) {
        DetailHeader(
            stringResource(R.string.map_static_pokemon, obj.level ?: 0),
            obj.pokemonName.orEmpty(),
            detail.roles
        ) {
            if (pokemonId != null) {
                PokemonSprite(
                    pokemonId,
                    SpritePlace.MAP_LIST,
                    SpriteSize.SHEET,
                    contentDescription = null,
                    shiny = obj.shiny
                )
            }
        }
    } else {
        DetailHeader("", obj.name, detail.roles) { CharacterSprite(obj, versionGroupIdentifier) }
    }
    if (pokemonId != null) {
        Button(onClick = { links.onOpenPokemon(pokemonId) }) {
            Text(stringResource(R.string.map_open_pokemon, obj.pokemonName.orEmpty()))
        }
    }
    if (detail.loading) {
        CircularProgressIndicator(Modifier.size(24.dp))
        return
    }
    if (detail.failed) {
        Text(stringResource(R.string.data_load_error), color = MaterialTheme.colorScheme.error)
        return
    }
    if (obj.kind == MapObjectKind.TRAINER) {
        if (detail.party.isEmpty()) {
            Text(stringResource(R.string.map_trainer_starter), style = MaterialTheme.typography.bodyMedium)
        } else {
            SectionTitle(stringResource(R.string.map_trainer_party))
            detail.party.forEach { TrainerPokemonRow(it, SpritePlace.MAP_LIST, links.onOpenPokemon) }
        }
    }
    // Un personnage qui n'a rien à donner, vendre ni échanger : rien de plus à afficher.
    Offers(
        detail.offers,
        SpritePlace.MAP_LIST,
        detail.fossilUses,
        onOpenPokemon = links.onOpenPokemon,
        onOpenItem = links.onOpenItem,
        onShowObject = links.onShowObject
    )
}

private val DETAIL_MAX_HEIGHT = 360.dp

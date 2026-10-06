package org.opensources.pokmaps.ui.pokemon

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.FilterQuality
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import coil3.compose.AsyncImage
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.domain.pokemon.PokemonDetails
import org.opensources.pokmaps.ui.common.AnimatedPokemonSprite
import org.opensources.pokmaps.ui.common.AssetImage
import org.opensources.pokmaps.ui.common.CaughtButton
import org.opensources.pokmaps.ui.common.FavoriteButton
import org.opensources.pokmaps.ui.common.LocalAnimatedSprites
import org.opensources.pokmaps.ui.common.TypeBadge
import org.opensources.pokmaps.ui.common.formatNumber

/** En-tête de la fiche : collection, image, identité et description du Pokémon. */
@Composable
internal fun PokemonHeader(
    details: PokemonDetails,
    game: Game,
    caught: Boolean,
    favorite: Boolean,
    onToggleCaught: () -> Unit,
    onToggleFavorite: () -> Unit
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(4.dp),
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp)
    ) {
        CollectionRow(game, caught, favorite, onToggleCaught, onToggleFavorite)
        PokemonImage(details)
        Identity(details)
    }
}

/** Capturé dans la version choisie, et favori (commun à tous les jeux). */
@Composable
private fun CollectionRow(
    game: Game,
    caught: Boolean,
    favorite: Boolean,
    onToggleCaught: () -> Unit,
    onToggleFavorite: () -> Unit
) {
    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
        CaughtButton(caught, onToggleCaught)
        Text(
            stringResource(if (caught) R.string.collection_caught_in else R.string.collection_not_caught_in, game.name),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.weight(1f)
        )
        FavoriteButton(favorite, onToggleFavorite)
    }
}

/** Sprite du jeu (animé selon le réglage) ou artwork officiel, chargé en ligne à la demande. */
@Composable
private fun PokemonImage(details: PokemonDetails) {
    var showArtwork by rememberSaveable(details.id) { mutableStateOf(false) }
    var artworkFailed by remember(details.id) { mutableStateOf(false) }
    Box(Modifier.size(SPRITE_SIZE), contentAlignment = Alignment.Center) {
        if (showArtwork && !artworkFailed) {
            AsyncImage(
                model = Sprites.officialArtwork(details.id),
                contentDescription = details.name,
                filterQuality = FilterQuality.Medium,
                onError = { artworkFailed = true },
                modifier = Modifier.fillMaxSize()
            )
        } else if (LocalAnimatedSprites.current) {
            AnimatedPokemonSprite(details.id, details.name, Modifier.fillMaxSize())
        } else {
            AssetImage(details.spritePath ?: details.iconPath, details.name, Modifier.fillMaxSize())
        }
    }
    TextButton(onClick = { showArtwork = !showArtwork }) {
        Icon(
            painterResource(R.drawable.ic_image),
            contentDescription = null,
            modifier = Modifier.padding(end = 8.dp)
        )
        Text(stringResource(if (showArtwork) R.string.pokemon_show_sprite else R.string.pokemon_show_artwork))
    }
    if (showArtwork && artworkFailed) {
        Text(
            stringResource(R.string.pokemon_artwork_error),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.error
        )
    }
}

/** Numéro, nom, catégorie, types, mensurations, capture, croissance et description. */
@Composable
private fun Identity(details: PokemonDetails) {
    details.number?.let {
        Text(stringResource(R.string.pokedex_number, it), color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
    Text(details.name, style = MaterialTheme.typography.headlineMedium)
    Text(
        details.genus,
        style = MaterialTheme.typography.titleSmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant
    )
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) { details.types.forEach { TypeBadge(it) } }
    Text(
        stringResource(
            R.string.pokemon_size,
            formatNumber(details.heightDm / 10.0),
            formatNumber(details.weightHg / 10.0)
        ),
        style = MaterialTheme.typography.bodyMedium
    )
    Text(
        stringResource(R.string.pokemon_capture_rate, details.captureRate) + " · " +
            stringResource(R.string.pokemon_growth, details.growthRate),
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant
    )
    details.description?.let {
        Text(it, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(top = 8.dp))
    }
}

private val SPRITE_SIZE = 160.dp

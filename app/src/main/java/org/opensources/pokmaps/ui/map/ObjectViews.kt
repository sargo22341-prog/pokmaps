package org.opensources.pokmaps.ui.map

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.map.NpcOffer
import org.opensources.pokmaps.domain.map.OfferItem
import org.opensources.pokmaps.domain.map.TrainerPokemon
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.domain.pokemon.LearnedMove
import org.opensources.pokmaps.ui.common.PixelArt
import org.opensources.pokmaps.ui.common.PixelArtImage
import org.opensources.pokmaps.ui.common.TypeBadge
import org.opensources.pokmaps.ui.common.label

// Éléments communs aux fiches de la carte et aux fiches de la recherche (objets, personnages, dresseurs).

/** Nom d'un personnage de la carte : classe du dresseur, Pokémon fixe ou nom d'après son sprite. */
fun MapObject.displayName(): String = when (kind) {
    MapObjectKind.TRAINER -> trainerClass?.let(::trainerClassName) ?: npcName(sprite)
    MapObjectKind.POKEMON -> pokemonName ?: npcName(sprite)
    MapObjectKind.ITEM, MapObjectKind.HIDDEN_ITEM -> itemName ?: npcName(sprite)
    MapObjectKind.NPC -> npcName(sprite)
}

@Composable
internal fun CharacterSprite(obj: MapObject, versionGroupIdentifier: String, size: Int = 48) {
    val sprite = obj.sprite ?: return
    PixelArtImage(Sprites.mapSprite(versionGroupIdentifier, sprite), PixelArt.MAP_SPRITE, size.dp, null)
}

@Composable
internal fun SectionTitle(text: String, modifier: Modifier = Modifier) {
    Text(
        text,
        style = MaterialTheme.typography.titleSmall,
        color = MaterialTheme.colorScheme.primary,
        modifier = modifier.padding(top = 4.dp)
    )
}

/** Pokémon d'un dresseur : niveau et attaques qu'il utilisera. */
@Composable
internal fun TrainerPokemonRow(mon: TrainerPokemon, onOpenPokemon: (Int) -> Unit) {
    Column(
        verticalArrangement = Arrangement.spacedBy(2.dp),
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onOpenPokemon(mon.pokemonId) }
            .padding(vertical = 4.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            PixelArtImage(Sprites.pokemonIcon(mon.pokemonId), PixelArt.POKEMON_ICON, 48.dp, null)
            Text(mon.name, style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
            Text(stringResource(R.string.encounter_levels, mon.level), style = MaterialTheme.typography.titleSmall)
        }
        mon.moves.forEach { MoveLine(it, Modifier.padding(start = 16.dp)) }
    }
}

/** Attaque : nom, type et caractéristiques (catégorie, puissance, précision, PP). */
@Composable
internal fun MoveLine(move: LearnedMove, modifier: Modifier = Modifier) {
    val none = stringResource(R.string.no_value)
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        modifier = modifier
    ) {
        TypeBadge(move.type)
        Column(Modifier.weight(1f)) {
            Text(move.name, style = MaterialTheme.typography.bodyMedium)
            Text(
                listOf(
                    stringResource(move.damageClass.label),
                    "${stringResource(R.string.move_power)} ${move.power ?: none}",
                    "${stringResource(R.string.move_accuracy)} ${move.accuracy?.let { "$it %" } ?: none}",
                    "${stringResource(R.string.move_pp)} ${move.pp}"
                ).joinToString(" · "),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

/** Dons, ventes et échanges d'un personnage ; objets et Pokémon ouvrent leur fiche si demandé. */
@Composable
internal fun Offers(
    offers: List<NpcOffer>,
    onOpenPokemon: ((Int) -> Unit)? = null,
    onOpenItem: ((String) -> Unit)? = null
) {
    val gifts = offers.filter { it is NpcOffer.GiftItem || it is NpcOffer.GiftPokemon }
    val sales = offers.filterIsInstance<NpcOffer.Sale>()
    val trades = offers.filterIsInstance<NpcOffer.Trade>()
    if (gifts.isNotEmpty()) {
        SectionTitle(stringResource(R.string.map_offer_gifts))
        gifts.forEach { offer ->
            when (offer) {
                is NpcOffer.GiftItem -> OfferItemRow(
                    offer.item,
                    if (offer.quantity > 1) {
                        stringResource(R.string.map_offer_quantity, offer.item.name, offer.quantity)
                    } else {
                        offer.item.name
                    },
                    onOpenItem = onOpenItem
                )

                is NpcOffer.GiftPokemon -> OfferPokemonRow(
                    offer.pokemonId,
                    offer.level?.let { stringResource(R.string.map_offer_pokemon_level, offer.name, it) }
                        ?: offer.name,
                    onOpenPokemon
                )

                else -> Unit
            }
        }
    }
    if (sales.isNotEmpty()) {
        SectionTitle(stringResource(R.string.map_offer_sales))
        sales.forEach { sale ->
            OfferItemRow(
                sale.item,
                sale.item.name,
                sale.price?.let { stringResource(R.string.map_offer_price, it) },
                onOpenItem
            )
        }
    }
    if (trades.isNotEmpty()) {
        SectionTitle(stringResource(R.string.method_trade))
        trades.forEach { trade ->
            OfferPokemonRow(
                trade.pokemonId,
                stringResource(R.string.map_offer_trade, trade.name, trade.wantedName),
                onOpenPokemon
            )
        }
    }
}

@Composable
private fun OfferItemRow(
    item: OfferItem,
    text: String,
    trailing: String? = null,
    onOpenItem: ((String) -> Unit)? = null
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        modifier = Modifier
            .fillMaxWidth()
            .clickable(enabled = onOpenItem != null) { onOpenItem?.invoke(item.identifier) }
    ) {
        if (item.hasSprite) {
            PixelArtImage(Sprites.item(item.identifier), PixelArt.ITEM_ICON, 32.dp, null)
        } else {
            Box(Modifier.size(32.dp))
        }
        Text(text, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.weight(1f))
        trailing?.let { Text(it, style = MaterialTheme.typography.titleSmall) }
    }
}

@Composable
private fun OfferPokemonRow(pokemonId: Int, text: String, onOpenPokemon: ((Int) -> Unit)?) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        modifier = Modifier
            .fillMaxWidth()
            .clickable(enabled = onOpenPokemon != null) { onOpenPokemon?.invoke(pokemonId) }
    ) {
        PixelArtImage(Sprites.pokemonIcon(pokemonId), PixelArt.POKEMON_ICON, 48.dp, null)
        Text(text, style = MaterialTheme.typography.bodyMedium)
    }
}

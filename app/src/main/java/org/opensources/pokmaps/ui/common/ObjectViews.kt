package org.opensources.pokmaps.ui.common

import androidx.annotation.StringRes
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
import org.opensources.pokmaps.domain.map.NpcOffer
import org.opensources.pokmaps.domain.map.OfferItem
import org.opensources.pokmaps.domain.map.OfferKind
import org.opensources.pokmaps.domain.map.OfferLink
import org.opensources.pokmaps.domain.map.TrainerPokemon
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.domain.pokemon.DamageClass
import org.opensources.pokmaps.domain.pokemon.LearnedMove

// Éléments communs aux fiches de la carte, aux fiches et à la recherche (objets, personnages, dresseurs).

@Composable
fun CharacterSprite(obj: MapObject, versionGroupIdentifier: String, size: Int = 48) {
    val sprite = obj.sprite ?: return
    PixelArtImage(Sprites.mapSprite(versionGroupIdentifier, sprite), PixelArt.MAP_SPRITE, size.dp, null)
}

@Composable
fun SectionTitle(text: String, modifier: Modifier = Modifier) {
    Text(
        text,
        style = MaterialTheme.typography.titleSmall,
        color = MaterialTheme.colorScheme.primary,
        modifier = modifier.padding(top = 4.dp)
    )
}

/** Pokémon d'un dresseur : niveau et attaques qu'il utilisera. */
@Composable
fun TrainerPokemonRow(mon: TrainerPokemon, onOpenPokemon: (Int) -> Unit) {
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
fun MoveLine(move: LearnedMove, modifier: Modifier = Modifier) {
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
fun Offers(offers: List<NpcOffer>, onOpenPokemon: ((Int) -> Unit)? = null, onOpenItem: ((String) -> Unit)? = null) {
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

                is NpcOffer.Sale, is NpcOffer.Trade -> Unit
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

@get:StringRes
val DamageClass.label: Int
    get() = when (this) {
        DamageClass.PHYSICAL -> R.string.damage_physical
        DamageClass.SPECIAL -> R.string.damage_special
        DamageClass.STATUS -> R.string.status_label
    }

/** « Donne CT28 · Vend Poké Ball, Potion · Échange Lippoutou » */
@Composable
fun offersSummary(offers: List<OfferLink>): String {
    fun names(name: (OfferLink) -> String?) = offers.mapNotNull(name).distinct().joinToString(", ")

    val byKind = offers.groupBy { it.kind }
    val gifts = names { offer ->
        when (offer.kind) {
            OfferKind.GIFT_ITEM -> offer.itemName
            OfferKind.GIFT_POKEMON -> offer.pokemonName
            OfferKind.SALE, OfferKind.TRADE -> null
        }
    }
    val sales = byKind[OfferKind.SALE].orEmpty().mapNotNull { it.itemName }.distinct().joinToString(", ")
    val trades = byKind[OfferKind.TRADE].orEmpty().mapNotNull { it.pokemonName }.distinct().joinToString(", ")
    return listOfNotNull(
        gifts.takeIf { it.isNotEmpty() }?.let { stringResource(R.string.offer_summary_gifts, it) },
        sales.takeIf { it.isNotEmpty() }?.let { stringResource(R.string.offer_summary_sales, it) },
        trades.takeIf { it.isNotEmpty() }?.let { stringResource(R.string.offer_summary_trades, it) }
    ).joinToString(" · ")
}

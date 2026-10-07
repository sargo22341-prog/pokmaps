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
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.map.CharacterRole
import org.opensources.pokmaps.domain.map.CharacterService
import org.opensources.pokmaps.domain.map.FossilUse
import org.opensources.pokmaps.domain.map.NpcOffer
import org.opensources.pokmaps.domain.map.OfferItem
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.domain.model.Sprites

/**
 * Ce que propose un personnage ou une installation : services, dons, ventes, échanges, lots du Casino et fossiles
 * ranimés. Objets et Pokémon ouvrent leur fiche si demandé ; un fossile donné dit en quoi il se ranime, et où.
 */
@Composable
fun Offers(
    offers: List<NpcOffer>,
    place: SpritePlace,
    fossilUses: Map<String, FossilUse> = emptyMap(),
    onOpenPokemon: ((Int) -> Unit)? = null,
    onOpenItem: ((String) -> Unit)? = null,
    onShowObject: ((Int) -> Unit)? = null
) {
    val links = OfferLinks(place, onOpenPokemon, onOpenItem)
    Services(offers.filterIsInstance<NpcOffer.Service>())
    Gifts(offers, links, fossilUses, onShowObject)
    Sales(offers, links)
    Trades(offers, links)
    Prizes(offers, links)
    Fossils(offers.filterIsInstance<NpcOffer.FossilRevival>(), links)
}

/** Où sont dessinés les Pokémon (réglage des sprites animés) et quelles fiches s'ouvrent au toucher. */
data class OfferLinks(val place: SpritePlace, val onOpenPokemon: ((Int) -> Unit)?, val onOpenItem: ((String) -> Unit)?)

@Composable
private fun Services(services: List<NpcOffer.Service>) {
    if (services.isEmpty()) return
    SectionTitle(stringResource(R.string.map_offer_services))
    services.forEach { offer ->
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            RoleIcon(offer.service.role, size = 24.dp)
            Text(stringResource(offer.service.description), style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable
private fun Gifts(
    offers: List<NpcOffer>,
    links: OfferLinks,
    fossilUses: Map<String, FossilUse>,
    onShowObject: ((Int) -> Unit)?
) {
    val gifts = offers.filter { it is NpcOffer.GiftItem || it is NpcOffer.GiftPokemon || it is NpcOffer.CoinGift }
    if (gifts.isEmpty()) return
    SectionTitle(stringResource(R.string.map_offer_gifts))
    gifts.forEach { offer ->
        when (offer) {
            is NpcOffer.GiftItem -> {
                OfferItemRow(offer.item, quantityText(offer.item.name, offer.quantity), onOpenItem = links.onOpenItem)
                fossilUses[offer.item.identifier]?.let { FossilUseLine(it, links, onShowObject) }
            }

            is NpcOffer.GiftPokemon -> OfferPokemonRow(
                offer.pokemonId,
                offer.level?.let { stringResource(R.string.map_offer_pokemon_level, offer.name, it) } ?: offer.name,
                links
            )

            is NpcOffer.CoinGift -> CoinRow(pluralStringResource(R.plurals.coins, offer.coins, offer.coins))

            else -> Unit
        }
    }
}

@Composable
private fun Sales(offers: List<NpcOffer>, links: OfferLinks) {
    val sales = offers.filter { it is NpcOffer.Sale || it is NpcOffer.CoinSale }
    if (sales.isEmpty()) return
    SectionTitle(stringResource(R.string.map_offer_sales))
    sales.forEach { offer ->
        when (offer) {
            is NpcOffer.Sale -> OfferItemRow(
                offer.item,
                offer.item.name,
                offer.price?.let { stringResource(R.string.map_offer_price, it) },
                links.onOpenItem
            )

            is NpcOffer.CoinSale -> CoinRow(
                pluralStringResource(R.plurals.coins, offer.coins, offer.coins),
                stringResource(R.string.map_offer_price, offer.price)
            )

            else -> Unit
        }
    }
}

@Composable
private fun Trades(offers: List<NpcOffer>, links: OfferLinks) {
    val trades = offers.filter { it is NpcOffer.Trade || it is NpcOffer.Exchange }
    if (trades.isEmpty()) return
    SectionTitle(stringResource(R.string.method_trade))
    trades.forEach { offer ->
        when (offer) {
            is NpcOffer.Trade -> OfferPokemonRow(
                offer.pokemonId,
                stringResource(R.string.map_offer_trade, offer.name, offer.wantedName),
                links
            )

            is NpcOffer.Exchange -> ExchangeRow(offer, links.onOpenItem)

            else -> Unit
        }
    }
}

@Composable
private fun Prizes(offers: List<NpcOffer>, links: OfferLinks) {
    val prizes = offers.filter { it is NpcOffer.PrizePokemon || it is NpcOffer.PrizeItem }
    if (prizes.isEmpty()) return
    SectionTitle(stringResource(R.string.map_offer_prizes))
    prizes.forEach { offer ->
        when (offer) {
            is NpcOffer.PrizePokemon -> OfferPokemonRow(
                offer.pokemonId,
                stringResource(R.string.map_offer_pokemon_level, offer.name, offer.level),
                links,
                pluralStringResource(R.plurals.coins, offer.coins, offer.coins)
            )

            is NpcOffer.PrizeItem -> OfferItemRow(
                offer.item,
                offer.item.name,
                pluralStringResource(R.plurals.coins, offer.coins, offer.coins),
                links.onOpenItem
            )

            else -> Unit
        }
    }
}

/** Fossiles que ranime le personnage, comme une ligne d'évolution : fossile → Pokémon. */
@Composable
private fun Fossils(revivals: List<NpcOffer.FossilRevival>, links: OfferLinks) {
    if (revivals.isEmpty()) return
    SectionTitle(stringResource(R.string.map_offer_fossils))
    revivals.forEach { revival ->
        FossilRevivalLine(
            fossil = revival.fossil,
            pokemonId = revival.pokemonId,
            text = stringResource(R.string.map_offer_pokemon_level, revival.name, revival.level),
            links = links
        )
    }
}

/**
 * Ce que devient un fossile donné ici, comme une ligne d'évolution (→ Pokémon ranimé), qui le ranime et où, et
 * bouton pour aller voir ce personnage sur la carte.
 */
@Composable
private fun FossilUseLine(use: FossilUse, links: OfferLinks, onShowObject: ((Int) -> Unit)?) {
    Column(Modifier.padding(start = 16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier
                .fillMaxWidth()
                .clickable(enabled = links.onOpenPokemon != null) { links.onOpenPokemon?.invoke(use.pokemonId) }
        ) {
            Text(stringResource(R.string.evolution_arrow), style = MaterialTheme.typography.titleLarge)
            PokemonSprite(use.pokemonId, links.place, SpriteSize.SHEET, contentDescription = null)
            Text(
                stringResource(R.string.map_offer_pokemon_level, use.pokemonName, use.level),
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.weight(1f)
            )
        }
        Text(
            stringResource(R.string.fossil_use, use.reviver.name, use.reviverMapName),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        if (onShowObject != null) {
            FilledTonalButton(onClick = { onShowObject(use.reviver.id) }) {
                Icon(painterResource(R.drawable.ic_map), contentDescription = null, Modifier.padding(end = 8.dp))
                Text(stringResource(R.string.fossil_show_reviver))
            }
        }
    }
}

/** Fossile, flèche et Pokémon ranimé, comme une ligne d'évolution (fiche du Pokémon ou du fossile au toucher). */
@Composable
fun FossilRevivalLine(fossil: OfferItem, pokemonId: Int, text: String, links: OfferLinks) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        modifier = Modifier
            .fillMaxWidth()
            .clickable(enabled = links.onOpenPokemon != null) { links.onOpenPokemon?.invoke(pokemonId) }
    ) {
        ItemIcon(
            fossil,
            Modifier.clickable(enabled = links.onOpenItem != null) { links.onOpenItem?.invoke(fossil.identifier) },
            size = FOSSIL_ICON_SIZE
        )
        Text(stringResource(R.string.evolution_arrow), style = MaterialTheme.typography.titleLarge)
        PokemonSprite(pokemonId, links.place, SpriteSize.SHEET, contentDescription = null)
        Text(text, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.weight(1f))
    }
}

@Composable
private fun ExchangeRow(offer: NpcOffer.Exchange, onOpenItem: ((String) -> Unit)?) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        modifier = Modifier
            .fillMaxWidth()
            .clickable(enabled = onOpenItem != null) { onOpenItem?.invoke(offer.item.identifier) }
    ) {
        ItemIcon(offer.item)
        Text(
            stringResource(R.string.map_offer_exchange, offer.item.name, offer.wanted.name),
            style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.weight(1f)
        )
        ItemIcon(
            offer.wanted,
            Modifier.clickable(enabled = onOpenItem != null) { onOpenItem?.invoke(offer.wanted.identifier) }
        )
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
        ItemIcon(item)
        Text(text, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.weight(1f))
        trailing?.let { Text(it, style = MaterialTheme.typography.titleSmall) }
    }
}

@Composable
private fun OfferPokemonRow(pokemonId: Int, text: String, links: OfferLinks, trailing: String? = null) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        modifier = Modifier
            .fillMaxWidth()
            .clickable(enabled = links.onOpenPokemon != null) { links.onOpenPokemon?.invoke(pokemonId) }
    ) {
        PokemonSprite(pokemonId, links.place, SpriteSize.SHEET, contentDescription = null)
        Text(text, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.weight(1f))
        trailing?.let { Text(it, style = MaterialTheme.typography.titleSmall) }
    }
}

@Composable
private fun CoinRow(text: String, trailing: String? = null) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Box(Modifier.size(ITEM_ICON_SIZE), contentAlignment = Alignment.Center) {
            RoleIcon(CharacterRole.COINS, size = 24.dp)
        }
        Text(text, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.weight(1f))
        trailing?.let { Text(it, style = MaterialTheme.typography.titleSmall) }
    }
}

@Composable
private fun ItemIcon(item: OfferItem, modifier: Modifier = Modifier, size: Dp = ITEM_ICON_SIZE) {
    if (item.hasSprite) {
        PixelArtImage(Sprites.item(item.identifier), PixelArt.ITEM_ICON, size, item.name, modifier)
    } else {
        Box(modifier.size(size))
    }
}

@Composable
private fun quantityText(name: String, quantity: Int): String =
    if (quantity > 1) stringResource(R.string.map_offer_quantity, name, quantity) else name

private val CharacterService.role: CharacterRole
    get() = when (this) {
        CharacterService.HEAL -> CharacterRole.HEAL
        CharacterService.CABLE_CLUB -> CharacterRole.CABLE_CLUB
        CharacterService.NAME_RATER -> CharacterRole.NAME_RATER
        CharacterService.DAYCARE -> CharacterRole.DAYCARE
    }

@get:StringRes
private val CharacterService.description: Int
    get() = when (this) {
        CharacterService.HEAL -> R.string.service_heal
        CharacterService.CABLE_CLUB -> R.string.service_cable_club
        CharacterService.NAME_RATER -> R.string.service_name_rater
        CharacterService.DAYCARE -> R.string.service_daycare
    }

private val ITEM_ICON_SIZE = 32.dp

/** Fossile d'une ligne fossile → Pokémon, assez grand pour se lire à côté du sprite. */
private val FOSSIL_ICON_SIZE = 64.dp

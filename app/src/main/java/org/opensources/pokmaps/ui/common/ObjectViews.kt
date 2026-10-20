package org.opensources.pokmaps.ui.common

import androidx.annotation.DrawableRes
import androidx.annotation.StringRes
import androidx.compose.animation.Crossfade
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
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
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.map.FossilUse
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.opensources.pokmaps.domain.map.OfferKind
import org.opensources.pokmaps.domain.map.OfferLink
import org.opensources.pokmaps.domain.map.RivalChoice
import org.opensources.pokmaps.domain.map.TeamSelection
import org.opensources.pokmaps.domain.map.TrainerPokemon
import org.opensources.pokmaps.domain.map.TrainerTeam
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.domain.model.Sprites
import org.opensources.pokmaps.domain.pokemon.DamageClass
import org.opensources.pokmaps.domain.pokemon.LearnedMove
import org.opensources.pokmaps.domain.pokemon.MoveEffect

// Éléments communs aux fiches de la carte, aux fiches et à la recherche (objets, personnages, dresseurs).

/** Sprite d'un personnage sur la carte, ou icône d'une installation (distributeur, comptoir des lots). */
@Composable
fun CharacterSprite(obj: MapObject, versionGroupIdentifier: String, size: Int = 48) {
    val sprite = obj.sprite
    val facility = obj.kind.facilityIcon
    when {
        sprite != null ->
            PixelArtImage(Sprites.mapSprite(versionGroupIdentifier, sprite), PixelArt.MAP_SPRITE, size.dp, null)

        facility != null -> Icon(
            painterResource(facility),
            contentDescription = null,
            tint = MaterialTheme.colorScheme.primary,
            modifier = Modifier.size(size.dp)
        )
    }
}

/** Icône d'une installation (elle n'a pas de sprite : elle fait partie du décor), null pour le reste. */
@get:DrawableRes
val MapObjectKind.facilityIcon: Int?
    get() = when (this) {
        MapObjectKind.VENDING_MACHINE -> R.drawable.ic_drink

        MapObjectKind.PRIZE_VENDOR -> R.drawable.ic_role_prizes

        MapObjectKind.HEAL_SPOT -> R.drawable.ic_role_heal

        MapObjectKind.ITEM, MapObjectKind.HIDDEN_ITEM, MapObjectKind.TRAINER, MapObjectKind.POKEMON,
        MapObjectKind.NPC, MapObjectKind.NPC_OBJECT, MapObjectKind.NPC_POKEMON -> null
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

/** Premier combat par défaut ; les revanches et les variantes de la partie se choisissent séparément. */
@Composable
fun TrainerTeams(
    selection: TeamSelection,
    place: SpritePlace,
    choiceFailed: Boolean,
    onChooseRival: (RivalChoice) -> Unit,
    onOpenPokemon: (Int) -> Unit,
    header: (@Composable (List<TrainerTeam>) -> Unit)? = null
) {
    if (selection.unknown) {
        header?.invoke(emptyList())
        Text(stringResource(R.string.map_trainer_starter), style = MaterialTheme.typography.bodyMedium)
        return
    }
    var battle by remember(selection.variants, selection.battles) { mutableStateOf<Int?>(null) }
    var showMoves by remember(selection.shown) { mutableStateOf(false) }
    val selected = if (selection.shown.any { it.rematch == battle }) {
        battle
    } else {
        selection.shown.minByOrNull { it.rematch ?: 0 }?.rematch
    }
    val active = selection.shown.filter { it.rematch == selected }
    header?.invoke(active)
    TrainerBattleSelector(selection.shown, selected) { battle = it }
    RivalChoicePanel(selection.forBattle(selected), place, choiceFailed, onChooseRival)
    Crossfade(active, label = "trainerTeams") { teams ->
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            teams.forEach { team ->
                if (header == null) {
                    Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.TopEnd) { TrainerPartyBalls(team) }
                }
                team.members.forEach { TrainerPokemonRow(it, place, onOpenPokemon, showMoves) }
            }
        }
    }
    if (selection.shown.any { team -> team.members.any { it.moves.isNotEmpty() } }) {
        TextButton(onClick = { showMoves = !showMoves }) {
            Text(stringResource(if (showMoves) R.string.trainer_hide_moves else R.string.trainer_show_moves))
        }
    }
}

/** Pokémon d'un dresseur : niveau et attaques qu'il utilisera. */
@Composable
fun TrainerPokemonRow(
    mon: TrainerPokemon,
    place: SpritePlace,
    onOpenPokemon: (Int) -> Unit,
    showMoves: Boolean = true
) {
    Column(
        verticalArrangement = Arrangement.spacedBy(2.dp),
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 48.dp)
            .clickable { onOpenPokemon(mon.pokemonId) }
            .padding(vertical = 4.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            PokemonSprite(mon.pokemonId, place, SpriteSize.TRAINER, contentDescription = null)
            Text(mon.name, style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
            Text(stringResource(R.string.encounter_levels, mon.level), style = MaterialTheme.typography.titleSmall)
        }
        mon.heldItemName?.let { Text(stringResource(R.string.map_offer_held_item, it)) }
        if (showMoves) mon.moves.forEach { MoveLine(it, Modifier.padding(start = 16.dp)) }
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

/** Ce que fait une attaque, et la probabilité de son effet quand il n'est pas systématique. */
@Composable
fun MoveEffectText(effect: MoveEffect, modifier: Modifier = Modifier) {
    Column(modifier, verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text(effect.description, style = MaterialTheme.typography.bodyMedium)
        effect.chance?.let {
            Text(
                stringResource(R.string.move_effect_chance, formatNumber(it)),
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.Bold
            )
        }
    }
}

@get:StringRes
val DamageClass.label: Int
    get() = when (this) {
        DamageClass.PHYSICAL -> R.string.damage_physical
        DamageClass.SPECIAL -> R.string.damage_special
        DamageClass.STATUS -> R.string.status_label
    }

/** « Donne CT28 · Vend Poké Ball, Potion · Échange Lippoutou · Lots : Abra, CT23 · Ranime Kabuto » */
@Composable
fun offersSummary(offers: List<OfferLink>, fossilUses: Map<String, FossilUse> = emptyMap()): String {
    val coins = stringResource(R.string.role_coins)
    val parts = mutableListOf<String>()
    offerNames(offers, fossilUses, coins, GIFTS)?.let { parts += stringResource(R.string.offer_summary_gifts, it) }
    offerNames(offers, fossilUses, coins, SALES)?.let { parts += stringResource(R.string.offer_summary_sales, it) }
    offerNames(offers, fossilUses, coins, TRADES)?.let { parts += stringResource(R.string.offer_summary_trades, it) }
    offerNames(offers, fossilUses, coins, PRIZES)?.let { parts += stringResource(R.string.offer_summary_prizes, it) }
    offerNames(offers, fossilUses, coins, FOSSILS)?.let { parts += stringResource(R.string.offer_summary_fossils, it) }
    offerNames(offers, fossilUses, coins, TREES)?.let { parts += stringResource(R.string.offer_summary_fruit_tree, it) }
    return parts.joinToString(" · ")
}

/** Noms de ce que proposent les offres de ces natures (null s'il n'y en a pas). */
@Composable
private fun offerNames(
    offers: List<OfferLink>,
    fossilUses: Map<String, FossilUse>,
    coins: String,
    kinds: Set<OfferKind>
): String? {
    val names = offers.filter { it.kind in kinds }.mapNotNull { offer ->
        val fossil = offer.itemIdentifier?.let { fossilUses[it] }
        when {
            offer.kind == OfferKind.COIN_SALE || offer.kind == OfferKind.COIN_GIFT -> coins

            offer.kind == OfferKind.FOSSIL -> offer.pokemonName

            offer.kind == OfferKind.GIFT_ITEM && fossil != null ->
                stringResource(R.string.offer_summary_fossil_gift, fossil.fossilName, fossil.pokemonName)

            else -> offer.itemName ?: offer.pokemonName
        }
    }.distinct()
    return names.takeIf { it.isNotEmpty() }?.joinToString(", ")
}

private val GIFTS = setOf(OfferKind.GIFT_ITEM, OfferKind.GIFT_POKEMON, OfferKind.GIFT_EGG, OfferKind.COIN_GIFT)
private val SALES = setOf(OfferKind.SALE, OfferKind.COIN_SALE)
private val TRADES = setOf(OfferKind.TRADE, OfferKind.EXCHANGE)
private val PRIZES = setOf(OfferKind.PRIZE_ITEM, OfferKind.PRIZE_POKEMON, OfferKind.POINT_PRIZE)
private val FOSSILS = setOf(OfferKind.FOSSIL)
private val TREES = setOf(OfferKind.FRUIT_TREE)

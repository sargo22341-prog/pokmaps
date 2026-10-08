package org.opensources.pokmaps.ui.common

import androidx.annotation.DrawableRes
import androidx.annotation.StringRes
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.map.CharacterRole

/**
 * Ce qu'est un élément de la carte et ce qu'on peut y faire, en icônes : épées croisées pour un dresseur,
 * silhouette pour un personnage, puis ses fonctions (soins, boutique, dons, échanges, lots…). Chaque icône est
 * décrite pour les lecteurs d'écran.
 */
@Composable
fun RoleIcons(roles: List<CharacterRole>, modifier: Modifier = Modifier, size: Dp = ROLE_ICON_SIZE) {
    if (roles.isEmpty()) return
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp),
        modifier = modifier
    ) {
        roles.forEach { role -> RoleIcon(role, size) }
    }
}

@Composable
fun RoleIcon(role: CharacterRole, size: Dp = ROLE_ICON_SIZE) {
    Icon(
        painterResource(role.icon),
        contentDescription = stringResource(role.label),
        tint = role.color ?: MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = Modifier.size(size)
    )
}

@get:DrawableRes
val CharacterRole.icon: Int
    get() = when (this) {
        CharacterRole.BATTLE -> R.drawable.ic_role_battle
        CharacterRole.CHARACTER -> R.drawable.ic_role_character
        CharacterRole.OBJECT -> R.drawable.ic_role_object
        CharacterRole.POKEMON -> R.drawable.ic_role_pokemon
        CharacterRole.HEAL -> R.drawable.ic_role_heal
        CharacterRole.SHOP -> R.drawable.ic_role_shop
        CharacterRole.GIFT -> R.drawable.ic_role_gift
        CharacterRole.TRADE -> R.drawable.ic_role_trade
        CharacterRole.PRIZES -> R.drawable.ic_role_prizes
        CharacterRole.COINS -> R.drawable.ic_role_coins
        CharacterRole.FOSSIL -> R.drawable.ic_role_fossil
        CharacterRole.FRUIT_TREE -> R.drawable.ic_role_fruit_tree
        CharacterRole.DAYCARE -> R.drawable.ic_role_daycare
        CharacterRole.NAME_RATER -> R.drawable.ic_role_name_rater
        CharacterRole.MOVE_DELETER -> R.drawable.ic_role_move_deleter
        CharacterRole.MOVE_TUTOR -> R.drawable.ic_role_move_tutor
        CharacterRole.GROOMING -> R.drawable.ic_role_grooming
        CharacterRole.CABLE_CLUB -> R.drawable.ic_role_cable_club
    }

@get:StringRes
val CharacterRole.label: Int
    get() = when (this) {
        CharacterRole.BATTLE -> R.string.role_battle
        CharacterRole.CHARACTER -> R.string.role_character
        CharacterRole.OBJECT -> R.string.map_item
        CharacterRole.POKEMON -> R.string.role_pokemon
        CharacterRole.HEAL -> R.string.role_heal
        CharacterRole.SHOP -> R.string.role_shop
        CharacterRole.GIFT -> R.string.role_gift
        CharacterRole.TRADE -> R.string.method_trade
        CharacterRole.PRIZES -> R.string.map_offer_prizes
        CharacterRole.COINS -> R.string.role_coins
        CharacterRole.FOSSIL -> R.string.map_offer_fossils
        CharacterRole.FRUIT_TREE -> R.string.role_fruit_tree
        CharacterRole.DAYCARE -> R.string.role_daycare
        CharacterRole.NAME_RATER -> R.string.role_name_rater
        CharacterRole.MOVE_DELETER -> R.string.role_move_deleter
        CharacterRole.MOVE_TUTOR -> R.string.role_move_tutor
        CharacterRole.GROOMING -> R.string.role_grooming
        CharacterRole.CABLE_CLUB -> R.string.role_cable_club
    }

/** Couleur de l'icône, lisible en thème clair comme sombre ; null : couleur du texte secondaire. */
private val CharacterRole.color: Color?
    get() = when (this) {
        CharacterRole.BATTLE -> Color(0xFFE53935)
        CharacterRole.CHARACTER, CharacterRole.OBJECT -> null
        CharacterRole.POKEMON -> Color(0xFFEF5350)
        CharacterRole.HEAL -> Color(0xFFEC407A)
        CharacterRole.SHOP -> Color(0xFF1E88E5)
        CharacterRole.GIFT -> Color(0xFF43A047)
        CharacterRole.TRADE -> Color(0xFFFB8C00)
        CharacterRole.PRIZES -> Color(0xFFFFB300)
        CharacterRole.COINS -> Color(0xFFC0A000)
        CharacterRole.FOSSIL -> Color(0xFF8D6E63)
        CharacterRole.FRUIT_TREE -> Color(0xFF7CB342)
        CharacterRole.DAYCARE -> Color(0xFF26A69A)
        CharacterRole.NAME_RATER -> Color(0xFF8E24AA)
        CharacterRole.MOVE_DELETER -> Color(0xFF78909C)
        CharacterRole.MOVE_TUTOR -> Color(0xFF00897B)
        CharacterRole.GROOMING -> Color(0xFFF06292)
        CharacterRole.CABLE_CLUB -> Color(0xFF5C6BC0)
    }

private val ROLE_ICON_SIZE = 20.dp

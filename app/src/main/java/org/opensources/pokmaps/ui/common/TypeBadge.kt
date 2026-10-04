package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.domain.model.PokemonType

/** Étiquette colorée d'un type (« Feu », « Eau »…). */
@Composable
fun TypeBadge(type: PokemonType, modifier: Modifier = Modifier) {
    val color = typeColor(type.identifier)
    Text(
        text = type.name,
        color = if (color.luminance() > 0.5f) Color.Black else Color.White,
        style = MaterialTheme.typography.labelMedium,
        maxLines = 1,
        modifier = modifier
            .background(color, RoundedCornerShape(50))
            .padding(horizontal = 8.dp, vertical = 2.dp)
    )
}

fun typeColor(identifier: String): Color = when (identifier) {
    "normal" -> Color(0xFFA8A878)
    "fighting" -> Color(0xFFC03028)
    "flying" -> Color(0xFFA890F0)
    "poison" -> Color(0xFFA040A0)
    "ground" -> Color(0xFFE0C068)
    "rock" -> Color(0xFFB8A038)
    "bug" -> Color(0xFFA8B820)
    "ghost" -> Color(0xFF705898)
    "steel" -> Color(0xFFB8B8D0)
    "fire" -> Color(0xFFF08030)
    "water" -> Color(0xFF6890F0)
    "grass" -> Color(0xFF78C850)
    "electric" -> Color(0xFFF8D030)
    "psychic" -> Color(0xFFF85888)
    "ice" -> Color(0xFF98D8D8)
    "dragon" -> Color(0xFF7038F8)
    "dark" -> Color(0xFF705848)
    "fairy" -> Color(0xFFEE99AC)
    else -> Color(0xFF68A090)
}

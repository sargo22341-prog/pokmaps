package org.opensources.pokmaps.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val DarkColors = darkColorScheme(primary = Color.White)

/**
 * Thème sombre unique de l'application, indépendant du thème et des couleurs du système.
 */
@Composable
fun PokemapsTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = DarkColors, content = content)
}

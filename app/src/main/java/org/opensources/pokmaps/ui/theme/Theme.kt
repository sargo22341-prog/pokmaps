package org.opensources.pokmaps.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext

private val PokeRed = Color(0xFFE3350D)
private val PokeRedDark = Color(0xFFFFB4A2)

private val LightColors = lightColorScheme(primary = PokeRed)
private val DarkColors = darkColorScheme(primary = PokeRedDark)

/**
 * Thème de l'application. Les couleurs dynamiques (Material You) sont utilisées par défaut ;
 * la palette rouge sert de repli (aperçus Compose, tests).
 */
@Composable
fun PokemapsTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = true,
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && darkTheme -> dynamicDarkColorScheme(LocalContext.current)
        dynamicColor -> dynamicLightColorScheme(LocalContext.current)
        darkTheme -> DarkColors
        else -> LightColors
    }
    MaterialTheme(colorScheme = colorScheme, content = content)
}

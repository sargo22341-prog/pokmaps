package io.github.sargo22341.pokmaps

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import io.github.sargo22341.pokmaps.ui.HomeScreen
import io.github.sargo22341.pokmaps.ui.theme.PokemapsTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            PokemapsTheme {
                HomeScreen()
            }
        }
    }
}

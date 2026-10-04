package org.opensources.pokmaps

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import dagger.hilt.android.AndroidEntryPoint
import org.opensources.pokmaps.ui.PokemapsApp
import org.opensources.pokmaps.ui.theme.PokemapsTheme

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            PokemapsTheme {
                PokemapsApp()
            }
        }
    }
}

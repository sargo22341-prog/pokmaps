package org.opensources.pokmaps.ui

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavHostController
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.ui.common.LocalAnimatedSprites
import org.opensources.pokmaps.ui.game.GameSelector
import org.opensources.pokmaps.ui.game.GameUiState
import org.opensources.pokmaps.ui.game.GameViewModel
import org.opensources.pokmaps.ui.settings.SettingsViewModel

@Composable
fun PokemapsApp(
    gameViewModel: GameViewModel = hiltViewModel(),
    settingsViewModel: SettingsViewModel = hiltViewModel()
) {
    val settings by settingsViewModel.state.collectAsStateWithLifecycle()
    val gameState by gameViewModel.state.collectAsStateWithLifecycle()
    CompositionLocalProvider(LocalAnimatedSprites provides settings.animatedSprites) {
        PokemapsContent(gameState, gameViewModel::select)
    }
}

@Composable
private fun PokemapsContent(gameState: GameUiState, onSelectGame: (Game) -> Unit) {
    val navController = rememberNavController()
    val backStackEntry by navController.currentBackStackEntryAsState()
    val route = backStackEntry?.destination?.route
    // Réglages et « À propos » : ni sélecteur de jeu ni barre de navigation.
    val isAbout = route == ABOUT_ROUTE || route == SETTINGS_ROUTE
    Scaffold(
        topBar = { PokemapsTopBar(route, isAbout, gameState, onSelectGame, navController) },
        bottomBar = { if (!isAbout) PokemapsBottomBar(route, navController) }
    ) { padding ->
        PokemapsNavHost(navController, Modifier.padding(padding))
    }
}

/** Titre (ou retour depuis une fiche), recherche, choix du jeu et réglages. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun PokemapsTopBar(
    route: String?,
    isAbout: Boolean,
    gameState: GameUiState,
    onSelectGame: (Game) -> Unit,
    navController: NavHostController
) {
    val detailTitle = DETAIL_TITLES[route]
    TopAppBar(
        title = { Text(stringResource(detailTitle ?: R.string.app_name)) },
        navigationIcon = {
            if (detailTitle != null) {
                IconButton(onClick = { navController.popBackStack() }) {
                    Icon(painterResource(R.drawable.ic_back), stringResource(R.string.back))
                }
            }
        },
        actions = {
            if (!isAbout) {
                if (route != SEARCH_ROUTE) {
                    IconButton(onClick = { navController.navigate(SEARCH_ROUTE) { launchSingleTop = true } }) {
                        Icon(painterResource(R.drawable.ic_search), stringResource(R.string.search_title))
                    }
                }
                GameSelector(gameState, onSelectGame)
                IconButton(onClick = { navController.navigate(SETTINGS_ROUTE) { launchSingleTop = true } }) {
                    Icon(painterResource(R.drawable.ic_settings), stringResource(R.string.settings_title))
                }
            }
        }
    )
}

/** Carte et Pokédex ; la fiche d'un Pokémon reste rattachée au Pokédex. */
@Composable
private fun PokemapsBottomBar(route: String?, navController: NavHostController) {
    NavigationBar {
        TopLevelDestination.entries.forEach { destination ->
            NavigationBarItem(
                selected = route == destination.route ||
                    (route == POKEMON_ROUTE && destination == TopLevelDestination.POKEDEX),
                onClick = { navController.navigateToTopLevel(destination) },
                icon = { Icon(painterResource(destination.icon), contentDescription = null) },
                label = { Text(stringResource(destination.label)) }
            )
        }
    }
}

package org.opensources.pokmaps.ui

import androidx.annotation.DrawableRes
import androidx.annotation.StringRes
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
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import org.opensources.pokmaps.R
import org.opensources.pokmaps.ui.about.AboutScreen
import org.opensources.pokmaps.ui.game.GameSelector
import org.opensources.pokmaps.ui.game.GameViewModel
import org.opensources.pokmaps.ui.map.MapScreen
import org.opensources.pokmaps.ui.pokedex.PokedexScreen
import org.opensources.pokmaps.ui.pokemon.PokemonScreen
import org.opensources.pokmaps.ui.pokemon.PokemonViewModel

/** Destinations principales, accessibles depuis la barre de navigation. */
enum class TopLevelDestination(val route: String, @StringRes val label: Int, @DrawableRes val icon: Int) {
    MAP("map", R.string.nav_map, R.drawable.ic_map),
    POKEDEX("pokedex", R.string.nav_pokedex, R.drawable.ic_pokedex)
}

private const val ABOUT_ROUTE = "about"
private const val POKEMON_ROUTE = "pokemon/{${PokemonViewModel.POKEMON_ID}}"

private fun pokemonRoute(pokemonId: Int) = "pokemon/$pokemonId"

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PokemapsApp(gameViewModel: GameViewModel = hiltViewModel()) {
    val navController = rememberNavController()
    val backStackEntry by navController.currentBackStackEntryAsState()
    val route = backStackEntry?.destination?.route
    val gameState by gameViewModel.state.collectAsStateWithLifecycle()
    val isAbout = route == ABOUT_ROUTE
    val isPokemon = route == POKEMON_ROUTE
    val openPokemon = { pokemonId: Int -> navController.navigate(pokemonRoute(pokemonId)) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        stringResource(
                            when {
                                isAbout -> R.string.about_title
                                isPokemon -> R.string.pokemon_title
                                else -> R.string.app_name
                            }
                        )
                    )
                },
                navigationIcon = {
                    if (isAbout || isPokemon) {
                        IconButton(onClick = { navController.popBackStack() }) {
                            Icon(painterResource(R.drawable.ic_back), stringResource(R.string.back))
                        }
                    }
                },
                actions = {
                    if (!isAbout) {
                        GameSelector(gameState, gameViewModel::select)
                        IconButton(onClick = { navController.navigate(ABOUT_ROUTE) }) {
                            Icon(painterResource(R.drawable.ic_info), stringResource(R.string.about_title))
                        }
                    }
                }
            )
        },
        bottomBar = {
            if (!isAbout) {
                NavigationBar {
                    TopLevelDestination.entries.forEach { destination ->
                        NavigationBarItem(
                            selected = route == destination.route ||
                                (isPokemon && destination == TopLevelDestination.POKEDEX),
                            onClick = { navController.navigateToTopLevel(destination) },
                            icon = { Icon(painterResource(destination.icon), contentDescription = null) },
                            label = { Text(stringResource(destination.label)) }
                        )
                    }
                }
            }
        }
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = TopLevelDestination.MAP.route,
            modifier = Modifier.padding(padding)
        ) {
            composable(TopLevelDestination.MAP.route) { MapScreen(onOpenPokemon = openPokemon) }
            composable(TopLevelDestination.POKEDEX.route) { PokedexScreen(onOpenPokemon = openPokemon) }
            composable(
                POKEMON_ROUTE,
                arguments = listOf(navArgument(PokemonViewModel.POKEMON_ID) { type = NavType.IntType })
            ) {
                PokemonScreen(
                    onOpenPokemon = openPokemon,
                    onShowOnMap = { navController.navigateToTopLevel(TopLevelDestination.MAP) }
                )
            }
            composable(ABOUT_ROUTE) { AboutScreen() }
        }
    }
}

private fun NavHostController.navigateToTopLevel(destination: TopLevelDestination) {
    navigate(destination.route) {
        popUpTo(graph.findStartDestination().id) { saveState = true }
        launchSingleTop = true
        restoreState = true
    }
}

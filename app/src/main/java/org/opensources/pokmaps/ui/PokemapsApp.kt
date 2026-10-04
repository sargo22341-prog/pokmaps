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
import org.opensources.pokmaps.ui.character.CharacterScreen
import org.opensources.pokmaps.ui.character.CharacterViewModel
import org.opensources.pokmaps.ui.game.GameSelector
import org.opensources.pokmaps.ui.game.GameViewModel
import org.opensources.pokmaps.ui.item.ItemScreen
import org.opensources.pokmaps.ui.item.ItemViewModel
import org.opensources.pokmaps.ui.map.MapScreen
import org.opensources.pokmaps.ui.place.PlaceScreen
import org.opensources.pokmaps.ui.place.PlaceViewModel
import org.opensources.pokmaps.ui.pokedex.PokedexScreen
import org.opensources.pokmaps.ui.pokemon.PokemonScreen
import org.opensources.pokmaps.ui.pokemon.PokemonViewModel
import org.opensources.pokmaps.ui.search.SearchScreen

/** Destinations principales, accessibles depuis la barre de navigation. */
enum class TopLevelDestination(val route: String, @StringRes val label: Int, @DrawableRes val icon: Int) {
    MAP("map", R.string.nav_map, R.drawable.ic_map),
    POKEDEX("pokedex", R.string.nav_pokedex, R.drawable.ic_pokedex)
}

private const val ABOUT_ROUTE = "about"
private const val SEARCH_ROUTE = "search"
private const val POKEMON_ROUTE = "pokemon/{${PokemonViewModel.POKEMON_ID}}"
private const val ITEM_ROUTE = "item/{${ItemViewModel.ITEM}}"
private const val PLACE_ROUTE = "place/{${PlaceViewModel.PLACE}}"
private const val CHARACTER_ROUTE = "character/{${CharacterViewModel.CHARACTER}}"

/** Titre de la barre du haut des écrans ouverts par-dessus la carte et le Pokédex. */
private val DETAIL_TITLES = mapOf(
    ABOUT_ROUTE to R.string.about_title,
    SEARCH_ROUTE to R.string.search_title,
    POKEMON_ROUTE to R.string.pokemon_title,
    ITEM_ROUTE to R.string.item_title,
    PLACE_ROUTE to R.string.place_title,
    CHARACTER_ROUTE to R.string.character_title
)

private fun pokemonRoute(pokemonId: Int) = "pokemon/$pokemonId"

private fun itemRoute(identifier: String) = "item/$identifier"

private fun placeRoute(identifier: String) = "place/$identifier"

private fun characterRoute(objectId: Int) = "character/$objectId"

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PokemapsApp(gameViewModel: GameViewModel = hiltViewModel()) {
    val navController = rememberNavController()
    val backStackEntry by navController.currentBackStackEntryAsState()
    val route = backStackEntry?.destination?.route
    val gameState by gameViewModel.state.collectAsStateWithLifecycle()
    val isAbout = route == ABOUT_ROUTE
    val detailTitle = DETAIL_TITLES[route]
    val openPokemon = { pokemonId: Int -> navController.navigate(pokemonRoute(pokemonId)) }
    val openItem = { identifier: String -> navController.navigate(itemRoute(identifier)) }
    val openPlace = { identifier: String -> navController.navigate(placeRoute(identifier)) }
    val openCharacter = { objectId: Int -> navController.navigate(characterRoute(objectId)) }
    val showMap = { navController.showMap() }

    Scaffold(
        topBar = {
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
                                (route == POKEMON_ROUTE && destination == TopLevelDestination.POKEDEX),
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
            composable(TopLevelDestination.MAP.route) { MapScreen(onOpenPokemon = openPokemon, onOpenItem = openItem) }
            composable(TopLevelDestination.POKEDEX.route) { PokedexScreen(onOpenPokemon = openPokemon) }
            composable(
                POKEMON_ROUTE,
                arguments = listOf(navArgument(PokemonViewModel.POKEMON_ID) { type = NavType.IntType })
            ) {
                PokemonScreen(onOpenPokemon = openPokemon, onOpenItem = openItem, onShowOnMap = showMap)
            }
            composable(SEARCH_ROUTE) {
                SearchScreen(
                    onOpenPokemon = openPokemon,
                    onOpenItem = openItem,
                    onOpenPlace = openPlace,
                    onOpenCharacter = openCharacter
                )
            }
            composable(ITEM_ROUTE, arguments = listOf(navArgument(ItemViewModel.ITEM) { type = NavType.StringType })) {
                ItemScreen(onOpenPokemon = openPokemon, onOpenCharacter = openCharacter, onShowOnMap = showMap)
            }
            composable(
                PLACE_ROUTE,
                arguments = listOf(navArgument(PlaceViewModel.PLACE) { type = NavType.StringType })
            ) {
                PlaceScreen(
                    onOpenPokemon = openPokemon,
                    onOpenItem = openItem,
                    onOpenPlace = openPlace,
                    onOpenCharacter = openCharacter,
                    onShowOnMap = showMap
                )
            }
            composable(
                CHARACTER_ROUTE,
                arguments = listOf(navArgument(CharacterViewModel.CHARACTER) { type = NavType.IntType })
            ) {
                CharacterScreen(
                    onOpenPokemon = openPokemon,
                    onOpenItem = openItem,
                    onOpenPlace = openPlace,
                    onShowOnMap = showMap
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
        // La carte est la destination de départ : restaurer son état remettrait par-dessus les écrans qu'on vient
        // de quitter (fiche d'objet, de Pokémon…) au lieu d'afficher la carte.
        restoreState = destination != TopLevelDestination.MAP
    }
}

/** « Voir sur la carte » : revient directement à la carte, en refermant les fiches ouvertes par-dessus. */
private fun NavHostController.showMap() {
    if (!popBackStack(TopLevelDestination.MAP.route, inclusive = false)) {
        navigateToTopLevel(TopLevelDestination.MAP)
    }
}

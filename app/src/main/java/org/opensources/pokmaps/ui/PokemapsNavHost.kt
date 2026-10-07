package org.opensources.pokmaps.ui

import androidx.annotation.DrawableRes
import androidx.annotation.StringRes
import androidx.compose.animation.AnimatedContentTransitionScope
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.scaleOut
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import org.opensources.pokmaps.R
import org.opensources.pokmaps.ui.about.AboutScreen
import org.opensources.pokmaps.ui.character.CharacterRoute
import org.opensources.pokmaps.ui.character.CharacterViewModel
import org.opensources.pokmaps.ui.game.GameRoute
import org.opensources.pokmaps.ui.item.ItemLinks
import org.opensources.pokmaps.ui.item.ItemRoute
import org.opensources.pokmaps.ui.item.ItemViewModel
import org.opensources.pokmaps.ui.map.MapRoute
import org.opensources.pokmaps.ui.move.MoveRoute
import org.opensources.pokmaps.ui.move.MoveViewModel
import org.opensources.pokmaps.ui.place.PlaceRoute
import org.opensources.pokmaps.ui.place.PlaceViewModel
import org.opensources.pokmaps.ui.pokedex.PokedexRoute
import org.opensources.pokmaps.ui.pokemon.PokemonLinks
import org.opensources.pokmaps.ui.pokemon.PokemonRoute
import org.opensources.pokmaps.ui.pokemon.PokemonViewModel
import org.opensources.pokmaps.ui.search.SearchRoute
import org.opensources.pokmaps.ui.settings.SettingsRoute

/** Destinations principales, accessibles depuis la barre de navigation. */
enum class TopLevelDestination(val route: String, @StringRes val label: Int, @DrawableRes val icon: Int) {
    MAP("map", R.string.nav_map, R.drawable.ic_map),
    POKEDEX("pokedex", R.string.nav_pokedex, R.drawable.ic_pokedex),
    GAME("game", R.string.nav_game, R.drawable.ic_cartridge)
}

internal const val ABOUT_ROUTE = "about"
internal const val SETTINGS_ROUTE = "settings"
internal const val SEARCH_ROUTE = "search"
internal const val POKEMON_ROUTE = "pokemon/{${PokemonViewModel.POKEMON_ID}}"
private const val ITEM_ROUTE = "item/{${ItemViewModel.ITEM}}"
private const val PLACE_ROUTE = "place/{${PlaceViewModel.PLACE}}"
private const val CHARACTER_ROUTE = "character/{${CharacterViewModel.CHARACTER}}"
private const val MOVE_ROUTE = "move/{${MoveViewModel.MOVE_ID}}"

/** Titre de la barre du haut des écrans ouverts par-dessus la carte et le Pokédex. */
internal val DETAIL_TITLES = mapOf(
    ABOUT_ROUTE to R.string.about_title,
    SETTINGS_ROUTE to R.string.settings_title,
    SEARCH_ROUTE to R.string.search_title,
    POKEMON_ROUTE to R.string.pokemon_title,
    ITEM_ROUTE to R.string.item_title,
    PLACE_ROUTE to R.string.place_title,
    CHARACTER_ROUTE to R.string.character_title,
    MOVE_ROUTE to R.string.move_title
)

/** Écrans de l'application et liens entre leurs fiches. */
@Composable
internal fun PokemapsNavHost(navController: NavHostController, modifier: Modifier = Modifier) {
    val openPokemon = { pokemonId: Int -> navController.navigate("pokemon/$pokemonId") }
    val openItem = { identifier: String -> navController.navigate("item/$identifier") }
    val openPlace = { identifier: String -> navController.navigate("place/$identifier") }
    val openCharacter = { objectId: Int -> navController.navigate("character/$objectId") }
    val openMove = { moveId: Int -> navController.navigate("move/$moveId") }
    val showMap = { navController.showMap() }
    NavHost(
        navController = navController,
        startDestination = TopLevelDestination.MAP.route,
        modifier = modifier,
        enterTransition = { navigationEnterTransition() },
        exitTransition = { navigationExitTransition() },
        popEnterTransition = { navigationEnterTransition() },
        popExitTransition = { navigationExitTransition() }
    ) {
        composable(TopLevelDestination.MAP.route) { MapRoute(onOpenPokemon = openPokemon, onOpenItem = openItem) }
        composable(TopLevelDestination.POKEDEX.route) { PokedexRoute(onOpenPokemon = openPokemon) }
        composable(TopLevelDestination.GAME.route) { GameRoute() }
        composable(POKEMON_ROUTE, listOf(navArgument(PokemonViewModel.POKEMON_ID) { type = NavType.IntType })) {
            PokemonRoute(PokemonLinks(openPokemon, openItem, openMove), onShowOnMap = showMap)
        }
        composable(MOVE_ROUTE, listOf(navArgument(MoveViewModel.MOVE_ID) { type = NavType.IntType })) {
            MoveRoute(onOpenPokemon = openPokemon, onOpenItem = openItem)
        }
        composable(SEARCH_ROUTE) {
            SearchRoute(openPokemon, openItem, openPlace, openCharacter)
        }
        composable(ITEM_ROUTE, listOf(navArgument(ItemViewModel.ITEM) { type = NavType.StringType })) {
            ItemRoute(ItemLinks(openPokemon, openCharacter, openMove), onShowOnMap = showMap)
        }
        composable(PLACE_ROUTE, listOf(navArgument(PlaceViewModel.PLACE) { type = NavType.StringType })) {
            PlaceRoute(openPokemon, openItem, openPlace, openCharacter, onShowOnMap = showMap)
        }
        composable(CHARACTER_ROUTE, listOf(navArgument(CharacterViewModel.CHARACTER) { type = NavType.IntType })) {
            CharacterRoute(openPokemon, openItem, openPlace, onShowOnMap = showMap)
        }
        composable(SETTINGS_ROUTE) { SettingsRoute(onOpenAbout = { navController.navigate(ABOUT_ROUTE) }) }
        composable(ABOUT_ROUTE) { AboutScreen() }
    }
}

private fun AnimatedContentTransitionScope<*>.navigationEnterTransition() =
    fadeIn(tween(NAVIGATION_TRANSITION_DURATION)) +
        scaleIn(initialScale = NAVIGATION_TRANSITION_SCALE, animationSpec = tween(NAVIGATION_TRANSITION_DURATION))

private fun AnimatedContentTransitionScope<*>.navigationExitTransition() =
    fadeOut(tween(NAVIGATION_TRANSITION_DURATION)) +
        scaleOut(targetScale = NAVIGATION_TRANSITION_SCALE, animationSpec = tween(NAVIGATION_TRANSITION_DURATION))

private const val NAVIGATION_TRANSITION_DURATION = 300
private const val NAVIGATION_TRANSITION_SCALE = 0.92f

internal fun NavHostController.navigateToTopLevel(destination: TopLevelDestination) {
    navigate(destination.route) {
        popUpTo(graph.findStartDestination().id) { saveState = true }
        launchSingleTop = true
        // Seul le Pokédex retrouve la fiche qu'on y avait ouverte. La carte est la destination de départ : restaurer
        // son état remettrait par-dessus les écrans qu'on vient de quitter (fiche d'objet, de Pokémon…) au lieu
        // d'afficher la carte ; de même, l'onglet « Jeu » affiche toujours la liste des jeux.
        restoreState = when (destination) {
            TopLevelDestination.MAP, TopLevelDestination.GAME -> false
            TopLevelDestination.POKEDEX -> true
        }
    }
}

/** « Voir sur la carte » : revient directement à la carte, en refermant les fiches ouvertes par-dessus. */
private fun NavHostController.showMap() {
    if (!popBackStack(TopLevelDestination.MAP.route, inclusive = false)) {
        navigateToTopLevel(TopLevelDestination.MAP)
    }
}

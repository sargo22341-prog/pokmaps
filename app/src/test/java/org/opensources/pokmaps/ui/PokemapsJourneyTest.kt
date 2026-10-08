package org.opensources.pokmaps.ui

import androidx.annotation.StringRes
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsNotSelected
import androidx.compose.ui.test.assertIsOff
import androidx.compose.ui.test.assertIsOn
import androidx.compose.ui.test.hasClickAction
import androidx.compose.ui.test.hasContentDescription
import androidx.compose.ui.test.hasScrollToNodeAction
import androidx.compose.ui.test.hasSetTextAction
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.isOff
import androidx.compose.ui.test.isSelected
import androidx.compose.ui.test.junit4.v2.createAndroidComposeRule
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performScrollToNode
import androidx.compose.ui.test.performTextInput
import dagger.hilt.android.testing.HiltAndroidRule
import dagger.hilt.android.testing.HiltAndroidTest
import dagger.hilt.android.testing.HiltTestApplication
import java.io.File
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.MainActivity
import org.opensources.pokmaps.R
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

/**
 * Parcours principaux sur l'application complète : vraie base générée, navigation, ViewModels et Hilt ;
 * seules les préférences sont neuves à chaque test (`TestSettingsModule`). La base versionnée doit être présente.
 */
@HiltAndroidTest
@RunWith(RobolectricTestRunner::class)
@Config(application = HiltTestApplication::class, qualifiers = "w411dp-h891dp")
class PokemapsJourneyTest {
    @get:Rule(order = 0)
    val hilt = HiltAndroidRule(this)

    @get:Rule(order = 1)
    val compose = createAndroidComposeRule<MainActivity>()

    @Before
    fun requireDatabase() {
        assertTrue(
            "Asset versionné absent : database/pokedex.db",
            File(System.getProperty("pokemaps.database").orEmpty()).isFile
        )
    }

    @Test
    fun crystalShowsTutorMovesAndTheirDetails() {
        selectGame("Cristal")
        openPokemon("pika", "Pikachu")
        compose.onNode(hasScrollToNodeAction()).performScrollToNode(hasText(text(R.string.pokemon_moves_tutor)))
        click(hasText(text(R.string.pokemon_moves_tutor)))
        compose.onNode(hasScrollToNodeAction()).performScrollToNode(hasText("Tonnerre"))
        click(hasText("Tonnerre"))
        await(hasText(text(R.string.move_title)))
    }

    @Test
    fun crystalShowsBothRegionsAndItsLegendaryEncounter() {
        selectGame("Cristal")
        click(hasText(text(R.string.nav_pokedex)))
        await(hasText(text(R.string.pokedex_filter_available, "Cristal")))
        type("suicune")
        click(hasText("Suicune"))
        await(hasScrollToNodeAction())
        compose.onNode(hasScrollToNodeAction()).performScrollToNode(hasText(text(R.string.show_on_map)))
        click(hasText(text(R.string.show_on_map)))
        await(hasText(text(R.string.map_highlight, "Suicune")))
        await(hasText("Johto"))
        click(hasText("Johto") and hasClickAction())
        await(hasText("Kanto"))
    }

    @Test
    fun crystalBuenaPrizesUseBlueCardPoints() {
        selectGame("Cristal")
        click(hasContentDescription(text(R.string.search_title)))
        type("buena")
        click(hasText("Récompenses de Buena"))
        await(hasText(text(R.string.character_title)))
        await(hasText("Récompenses"))
        compose.onAllNodes(hasText("2 points de la Carte Bleue")).assertCountEquals(2)
        compose.onNode(hasText("Lots, contre des jetons")).assertDoesNotExist()
    }

    @Test
    fun goldShowsBothRegionsAndTheNightFilter() {
        selectGold()
        click(hasText(text(R.string.nav_map)))
        await(hasText("Johto"))
        click(hasText("Johto") and hasClickAction())
        click(hasText("Kanto") and hasClickAction())
        compose.onNode(hasText("Kanto") and hasClickAction()).assertExists()
        click(hasText("Kanto") and hasClickAction())
        click(hasText("Johto") and hasClickAction())
        click(hasContentDescription(text(R.string.time_all)))
        click(hasContentDescription(text(R.string.time_morning)))
        click(hasContentDescription(text(R.string.time_day)))
        compose.onNode(hasContentDescription(text(R.string.time_night)) and hasClickAction()).assertExists()
        openPokemon("hoot", "Hoothoot")
        compose.onNode(hasScrollToNodeAction()).performScrollToNode(hasText(text(R.string.show_on_map)))
        click(hasText(text(R.string.show_on_map)))
        await(hasText(text(R.string.map_highlight, "Hoothoot")))
    }

    @Test
    fun goldShowsEggMovesAndOpensTheirDetails() {
        selectGold()
        openPokemon("pichu", "Pichu")
        compose.onNode(hasScrollToNodeAction()).performScrollToNode(hasText(text(R.string.pokemon_moves_egg)))
        click(hasText(text(R.string.pokemon_moves_egg)))
        compose.onNode(hasScrollToNodeAction()).performScrollToNode(hasText("Encore"))
        click(hasText("Encore"))
        await(hasText(text(R.string.move_title)))
    }

    @Test
    fun goldShowsHeldItemsAndBreeding() {
        selectGold()
        openPokemon("pika", "Pikachu")
        compose.onNode(hasScrollToNodeAction()).performScrollToNode(hasText(text(R.string.pokemon_held_items)))
        await(hasText("Baie Oran"))
        compose.onNode(hasScrollToNodeAction()).performScrollToNode(hasText(text(R.string.pokemon_breeding)))
        await(hasText(text(R.string.pokemon_hatch_cycles, 10)))
    }

    @Test
    fun goldShowsFriendshipAndTimeOfDayForEevee() {
        selectGold()
        openPokemon("evoli", "Évoli")
        compose.onNode(hasScrollToNodeAction()).performScrollToNode(hasText(text(R.string.pokemon_evolutions)))
        await(hasText(text(R.string.evolution_happiness, 220), substring = true))
        compose.onNode(hasText(text(R.string.evolution_day), substring = true)).assertExists()
        compose.onNode(hasText(text(R.string.evolution_night), substring = true)).assertExists()
    }

    @Test
    fun pokedexSearchOpensPokemonThenShowsItOnMap() {
        click(hasText(text(R.string.nav_pokedex)))
        type("pika")
        click(hasText("Pikachu"))
        await(hasScrollToNodeAction())
        compose.onNode(hasScrollToNodeAction()).performScrollToNode(hasText(text(R.string.show_on_map)))
        click(hasText(text(R.string.show_on_map)))

        // Retour sur la carte, avec les lieux de Pikachu surlignés.
        await(hasText(text(R.string.map_highlight, "Pikachu")))
        compose.onNode(hasText(text(R.string.pokemon_title))).assertDoesNotExist()
    }

    @Test
    fun caughtPokemonIsCountedInThePokedex() {
        click(hasText(text(R.string.nav_pokedex)))
        type("pika")
        click(hasText("Pikachu"))
        click(hasContentDescription(text(R.string.collection_not_caught)))
        await(hasContentDescription(text(R.string.collection_caught)))

        click(hasContentDescription(text(R.string.back)))
        // La recherche est gardée, et la capture comptée dans la version choisie (Rouge, le jeu par défaut).
        await(hasText(compose.activity.resources.getQuantityString(R.plurals.pokedex_count_caught, 1, 1, 1, 151)))
    }

    @Test
    fun globalSearchOpensPlaceThenShowsItOnMap() {
        click(hasContentDescription(text(R.string.search_title)))
        type("jadielle")
        click(hasText("Jadielle"))
        await(hasText(text(R.string.place_title)))

        click(hasText(text(R.string.show_on_map)))
        // La fiche est refermée et la carte s'ouvre sur la ville, dont elle affiche le nom.
        await(hasContentDescription(text(R.string.map_layers)))
        compose.onNode(hasText(text(R.string.place_title))).assertDoesNotExist()
        compose.onNode(hasText("Jadielle")).assertExists()
    }

    @Test
    fun globalSearchOpensItemSheet() {
        click(hasContentDescription(text(R.string.search_title)))
        type("pierre lune")
        await(hasText(text(R.string.search_items, 1)))
        click(hasText("Pierre Lune"))

        await(hasText(text(R.string.item_title)))
        // Pokémon que la Pierre Lune fait évoluer.
        await(hasText(text(R.string.item_evolution, "Mélofée", "Mélodelfe")))
    }

    @Test
    fun selectedGameAppliesToTheWholeApp() {
        // Le jeu se choisit dans l'onglet « Jeu » de la barre du bas ; la barre du haut affiche le jeu choisi.
        await(hasText(text(R.string.game_name, "Rouge")))
        click(hasText(text(R.string.nav_game)))
        await(hasText(text(R.string.game_generation, 1)))
        val yellow = hasContentDescription(text(R.string.game_cover, "Jaune"))
        compose.onNode(yellow).assertIsNotSelected().performClick()
        await(yellow and isSelected())
        // Une seule jaquette, sans titre dupliqué ; la barre du haut suit le choix.
        compose.onAllNodes(yellow).assertCountEquals(1)
        await(hasText(text(R.string.game_name, "Jaune")))
        compose.onNode(hasContentDescription(text(R.string.game_cover, "Rouge"))).assertIsNotSelected()

        click(hasContentDescription(text(R.string.search_title)))
        await(hasText(text(R.string.search_intro, "Jaune")))

        // Revenir à l'onglet « Jeu » depuis une fiche ouverte par-dessus affiche la liste des jeux, pas la fiche.
        click(hasText(text(R.string.nav_game)))
        await(hasText(text(R.string.game_generation, 1)))
        val search = hasText(text(R.string.search_intro, "Jaune"))
        compose.waitUntil(TIMEOUT_MS) { compose.onAllNodes(search).fetchSemanticsNodes().isEmpty() }
    }

    @Test
    fun aLevelUpMoveOpensItsSheet() {
        openPokemon("salam", "Salamèche")
        compose.onNode(hasScrollToNodeAction()).performScrollToNode(hasText("Groz’Yeux"))
        click(hasText("Groz’Yeux"))

        await(hasText(text(R.string.move_title)))
        await(hasText("Baisse la Défense de la cible d’un niveau."))
    }

    @Test
    fun aMachineMoveOpensTheMachineSheetWithItsEffect() {
        openPokemon("salam", "Salamèche")
        compose.onNode(hasScrollToNodeAction()).performScrollToNode(hasText(text(R.string.pokemon_moves_machine)))
        click(hasText(text(R.string.pokemon_moves_machine)))
        compose.onNode(hasScrollToNodeAction()).performScrollToNode(hasText("Plaquage"))
        click(hasText("Plaquage"))

        await(hasText(text(R.string.item_title)))
        await(hasText(text(R.string.map_machine_move, "Plaquage")))
        await(hasText(text(R.string.move_effect_chance, "30,1")))
        click(hasText(text(R.string.move_open)))
        await(hasText(text(R.string.move_title)))
    }

    @Test
    fun settingsAreSavedAndOpenAbout() {
        val animated = hasText(text(R.string.settings_animated_sprites))
        click(hasContentDescription(text(R.string.settings_title)))
        await(animated)
        // Animés au Pokédex et sur la fiche Pokémon par défaut : l'interrupteur général anime tout, et le choix est
        // mémorisé d'une visite des réglages à l'autre.
        compose.onNode(animated).assertIsOff().performClick()
        click(hasContentDescription(text(R.string.back)))
        click(hasContentDescription(text(R.string.settings_title)))
        await(animated)
        compose.onNode(animated).assertIsOn()
        // Le sous-menu choisit endroit par endroit : la carte seule redevient fixe.
        click(hasContentDescription(text(R.string.settings_animated_expand)))
        val map = hasText(text(R.string.nav_map))
        await(map)
        compose.onNode(map).assertIsOn().performClick()
        compose.waitUntil(TIMEOUT_MS) { compose.onAllNodes(map and isOff()).fetchSemanticsNodes().isNotEmpty() }
        compose.onNode(animated).assertIsOff()

        // Le sous-menu ouvert pousse « À propos » plus bas dans l'écran.
        await(hasText(text(R.string.about_title)))
        compose.onNode(hasText(text(R.string.about_title))).performScrollTo().performClick()
        await(hasText(text(R.string.about_credit_pokeapi_title)))
    }

    @Test
    fun unownFormsAreAccessibleFromTheirSheetAndPersist() {
        selectGold()
        openPokemon("zarbi", "Zarbi")
        click(hasText(text(R.string.unown_title)))
        await(hasText(text(R.string.unown_progress, 0, 26)))
        val form = hasContentDescription(text(R.string.unown_form, "A")) and hasClickAction()
        compose.onNode(form).assertIsOff().performClick()
        await(hasText(text(R.string.unown_progress, 1, 26)))
        compose.onNode(hasText(text(R.string.unown_form, "!"))).assertDoesNotExist()
    }

    private fun text(@StringRes id: Int, vararg args: Any): String = compose.activity.getString(id, *args)

    private fun selectGold() {
        selectGame("Or")
    }

    private fun selectGame(name: String) {
        click(hasText(text(R.string.nav_game)))
        await(hasScrollToNodeAction())
        compose.onNode(
            hasScrollToNodeAction() and SemanticsMatcher.keyIsDefined(SemanticsProperties.VerticalScrollAxisRange)
        ).performScrollToNode(hasContentDescription(text(R.string.game_cover, name)))
        click(hasContentDescription(text(R.string.game_cover, name)))
        compose.waitUntil(TIMEOUT_MS) {
            compose.onAllNodes(hasText(text(R.string.game_name, name))).fetchSemanticsNodes().size == 1
        }
    }

    /** Ouvre la fiche d'un Pokémon depuis le Pokédex. */
    private fun openPokemon(query: String, name: String) {
        click(hasText(text(R.string.nav_pokedex)))
        type(query)
        click(hasText(name))
        await(hasScrollToNodeAction())
    }

    /** Attend qu'un nœud apparaisse : les données sont lues hors du fil principal. */
    private fun await(matcher: SemanticsMatcher) {
        compose.waitUntil(TIMEOUT_MS) { compose.onAllNodes(matcher).fetchSemanticsNodes().isNotEmpty() }
    }

    private fun click(matcher: SemanticsMatcher) {
        await(matcher)
        compose.onNode(matcher).performClick()
    }

    /** Saisit du texte dans le seul champ de l'écran (recherche du Pokédex ou recherche globale). */
    private fun type(query: String) {
        await(hasSetTextAction())
        compose.onNode(hasSetTextAction()).performTextInput(query)
    }

    private companion object {
        const val TIMEOUT_MS = 10_000L
    }
}

package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.layout.Column
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.hasContentDescription
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.performClick
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.domain.map.TeamSelection
import org.opensources.pokmaps.domain.map.TrainerPokemon
import org.opensources.pokmaps.domain.map.TrainerTeam
import org.opensources.pokmaps.domain.model.SpritePlace
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class TrainerTeamsTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun firstBattleIsShownInitiallyAndRematchesReplaceIt() {
        val base = TrainerTeam(null, listOf(pokemon(16, "Roucool")))
        val rematch = TrainerTeam(null, listOf(pokemon(17, "Roucoups"), pokemon(19, "Rattata")), rematch = 1)
        compose.setContent {
            Column { TrainerTeams(TeamSelection(listOf(rematch, base)), SpritePlace.MAP_LIST, false, {}, {}) }
        }
        compose.onNode(hasText("Roucool")).assertExists()
        compose.onNode(hasText("Roucoups")).assertDoesNotExist()
        compose.onAllNodes(hasContentDescription("Un Pokémon dans l’équipe")).assertCountEquals(1)
        compose.onAllNodes(hasContentDescription("Place vide dans l’équipe")).assertCountEquals(5)
        compose.onNode(hasText("Premier combat")).performClick()
        compose.onNode(hasText("Revanche 1")).performClick()
        compose.onNode(hasText("Roucool")).assertDoesNotExist()
        compose.onNode(hasText("Roucoups")).assertExists()
        compose.onAllNodes(hasContentDescription("Un Pokémon dans l’équipe")).assertCountEquals(2)
        compose.onAllNodes(hasContentDescription("Place vide dans l’équipe")).assertCountEquals(4)
    }

    private fun pokemon(id: Int, name: String) = TrainerPokemon(id, name, 5, emptyList())

    @Test
    fun headerFollowsTheSelectedBattleWithoutDuplicatingPartyBalls() {
        val base = TrainerTeam(null, listOf(pokemon(16, "Roucool")))
        val rematch = TrainerTeam(null, listOf(pokemon(17, "Roucoups"), pokemon(19, "Rattata")), rematch = 1)
        compose.setContent {
            Column {
                TrainerTeams(
                    TeamSelection(listOf(base, rematch)),
                    SpritePlace.SHEETS,
                    false,
                    {},
                    {},
                    header = { teams -> teams.forEach { TrainerPartyBalls(it) } }
                )
            }
        }
        compose.onAllNodes(hasContentDescription("Un Pokémon dans l’équipe")).assertCountEquals(1)
        compose.onAllNodes(hasContentDescription("Place vide dans l’équipe")).assertCountEquals(5)
        compose.onNode(hasText("Premier combat")).performClick()
        compose.onNode(hasText("Revanche 1")).performClick()
        compose.onAllNodes(hasContentDescription("Un Pokémon dans l’équipe")).assertCountEquals(2)
        compose.onAllNodes(hasContentDescription("Place vide dans l’équipe")).assertCountEquals(4)
    }
}

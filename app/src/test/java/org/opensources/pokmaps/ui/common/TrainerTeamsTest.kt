package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.layout.Column
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.hasContentDescription
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.performClick
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.domain.map.RivalChoice
import org.opensources.pokmaps.domain.map.TeamSelection
import org.opensources.pokmaps.domain.map.TeamVariant
import org.opensources.pokmaps.domain.map.TeamVariantKind
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
    fun yellowOutcomesOnlyAppearOnTheSecondBattleAndChangingThemKeepsItOpen() {
        val fixed = TrainerTeam(null, listOf(pokemon(133, "Évoli")))
        val variants = listOf(134 to "Aquali", 135 to "Voltali", 136 to "Pyroli").map { (id, name) ->
            TrainerTeam(TeamVariant(TeamVariantKind.RIVAL_EVOLUTION, id, name), listOf(pokemon(id, name)), 1)
        }
        compose.setContent {
            var choice by remember { mutableStateOf(RivalChoice()) }
            Column {
                TrainerTeams(
                    TeamSelection.of(listOf(fixed) + variants, choice),
                    SpritePlace.MAP_LIST,
                    false,
                    { choice = it },
                    {}
                )
            }
        }
        compose.onNode(hasText("Évoli")).assertExists()
        compose.onNode(hasText("Vos premiers combats contre le rival")).assertDoesNotExist()
        compose.onNode(hasText("Premier combat")).performClick()
        compose.onNode(hasText("Combat 2")).performClick()
        compose.onNode(hasText("Voltali")).assertExists()
        compose.onNode(hasText("Victoire au laboratoire du Prof. Chen")).performClick()
        compose.onNode(hasText("Aquali")).assertExists()
        compose.onNode(hasText("Évoli")).assertDoesNotExist()
        compose.onNode(hasText("Combat 2")).performClick()
        compose.onNode(hasText("Premier combat")).performClick()
        compose.onNode(hasText("Évoli")).assertExists()
        compose.onNode(hasText("Vos premiers combats contre le rival")).assertDoesNotExist()
    }

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

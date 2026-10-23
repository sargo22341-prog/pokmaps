package org.opensources.pokmaps.ui.place

import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.v2.createComposeRule
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.domain.map.MapInfo
import org.opensources.pokmaps.domain.usecase.PlacePage
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class PlaceScreenTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun aDedicatedOutdoorMapIsNotCalledAnInterior() {
        val page = PlacePage(
            game = FakeGameDao.HEARTGOLD,
            map = MapInfo(1, "hgss-safari-zone-grassland", "Parc Safari — gabarit Prairie", null, 0, 0, 128, 128, 1),
            encounters = emptyList(),
            items = emptyList(),
            characters = emptyList(),
            offers = emptyMap(),
            places = emptyList()
        )
        compose.setContent {
            PlaceScreen(
                PlaceUiState(loading = false, page = page),
                onAction = {},
                onOpenPokemon = {},
                onOpenItem = {},
                onOpenPlace = {},
                onOpenCharacter = {}
            )
        }

        compose.onNode(hasText("Lieu")).assertExists()
        compose.onNode(hasText("Lieu intérieur")).assertDoesNotExist()
    }
}

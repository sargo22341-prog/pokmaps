package org.opensources.pokmaps.ui.map

import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.v2.createComposeRule
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.map.MapObjectKind
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class MapItemQuantityTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun hiddenItemDetailKeepsTheQuantityAnnotation() {
        compose.setContent {
            DetailCard(MapDetail.Item(honey), "platinum", false, {}, {}, {}, {}, {})
        }
        compose.onNode(hasText("Miel ×3")).assertExists()
        compose.onNode(hasText("Miel")).assertDoesNotExist()
    }

    @Test
    fun placeListKeepsTheQuantityAnnotation() {
        compose.setContent {
            ZoneListSheet(
                zone = MapZone(1, "Vieux Château", emptyList(), items = listOf(honey), loading = false),
                caught = emptySet(),
                onDismiss = {},
                onOpenPlace = {},
                onOpenPokemon = {},
                onOpenItem = {},
                onShowObject = {}
            )
        }
        compose.onNode(hasText("Miel ×3")).assertExists()
        compose.onNode(hasText("Miel")).assertDoesNotExist()
    }

    private val honey = MapObject(
        id = 1,
        mapId = 1,
        kind = MapObjectKind.HIDDEN_ITEM,
        x = 10,
        y = 20,
        sprite = null,
        itemId = 94,
        itemIdentifier = "honey",
        itemName = "Miel",
        pokemonId = null,
        pokemonName = null,
        level = null,
        trainerClass = null,
        name = "Miel ×3",
        itemHasSprite = false
    )
}

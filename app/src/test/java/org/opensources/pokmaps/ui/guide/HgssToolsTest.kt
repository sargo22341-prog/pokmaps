package org.opensources.pokmaps.ui.guide

import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.domain.guide.BreedingCatalog
import org.opensources.pokmaps.domain.guide.BreedingItem
import org.opensources.pokmaps.domain.guide.ParentSex
import org.opensources.pokmaps.domain.guide.ParentValues
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class HgssToolsTest {
    @get:Rule val compose = createComposeRule()

    @Test
    fun hgssResultExplainsDistinctIvsAndThePaternalEverstoneInFrench() {
        val state = BreedingUiState(
            loading = false,
            catalog = BreedingCatalog(FakeGameDao.HEARTGOLD, emptyList()),
            second = ParentValues(ParentSex.MALE, item = BreedingItem.EVERSTONE)
        )
        compose.setContent { GbaBreedingResult(state) }
        compose.onNodeWithText("Trois IV distincts sont hérités.", substring = true).assertExists()
        compose.onNodeWithText("Pierre Stase : parents éligibles 2.", substring = true).assertExists()
        compose.onNodeWithText("Les objets Pouvoir ne transmettent pas", substring = true).assertDoesNotExist()
    }
}

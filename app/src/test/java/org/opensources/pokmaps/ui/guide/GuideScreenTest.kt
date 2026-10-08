package org.opensources.pokmaps.ui.guide

import android.content.Context
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.isToggleable
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.performClick
import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.R
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.domain.guide.GuideArticle
import org.opensources.pokmaps.domain.guide.GuideCategory
import org.opensources.pokmaps.domain.guide.GuideLibrary
import org.opensources.pokmaps.domain.guide.GuideSpan
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class GuideScreenTest {
    @get:Rule val compose = createComposeRule()
    private val context: Context = ApplicationProvider.getApplicationContext()
    private val actions = mutableListOf<GuideAction>()

    private fun show(state: GuideUiState) {
        compose.setContent {
            GuideScreen(state, { actions += it }, GuideLinks({}, {}, {}), {})
        }
    }

    @Test
    fun emptyCatalogAndFailureAreDistinct() {
        show(GuideUiState(loading = false, library = GuideLibrary(FakeGameDao.RED, emptyList())))
        compose.onNode(hasText(context.getString(R.string.data_load_error))).assertDoesNotExist()
        compose.onNode(hasText(context.getString(R.string.nav_guides))).assertExists()
    }

    @Test
    fun failureShowsAnExplicitRetryAction() {
        show(GuideUiState(loading = false, failed = true))
        compose.onNode(hasText(context.getString(R.string.data_load_error))).assertExists()
        compose.onNode(hasText(context.getString(R.string.guide_retry))).performClick()
        assertEquals(listOf(GuideAction.Retry), actions)
    }

    @Test
    fun relatedTrophyOpensTheObjectiveAndCheckboxRemainsManual() {
        val objective = GuideArticle(
            "ra-1",
            "Objectif lié",
            GuideCategory.ACHIEVEMENT,
            listOf(listOf(GuideSpan("Condition française"))),
            25,
            emptyList(),
            missable = true,
            achievementId = 1
        )
        val chapter = GuideArticle(
            "chapter",
            "Étape test",
            GuideCategory.WALKTHROUGH,
            listOf(listOf(GuideSpan("Paragraphe"))),
            25,
            emptyList(),
            relatedIds = setOf("ra-1")
        )
        show(
            GuideUiState(
                loading = false,
                library = GuideLibrary(FakeGameDao.RED, listOf(chapter, objective)),
                category = GuideCategory.WALKTHROUGH,
                articleId = "chapter"
            )
        )
        compose.onNode(hasText(context.getString(R.string.guide_related_achievements, 1, 1))).performClick()
        compose.onNode(hasText("Objectif lié")).performClick()
        compose.onNode(isToggleable()).performClick()
        assertEquals(listOf(GuideAction.Article("ra-1"), GuideAction.Complete("chapter", true)), actions)
    }
}

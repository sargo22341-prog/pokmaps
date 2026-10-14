package org.opensources.pokmaps.ui.guide

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.isToggleable
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.performClick
import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.R
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.domain.guide.GuideArticle
import org.opensources.pokmaps.domain.guide.GuideCategory
import org.opensources.pokmaps.domain.guide.GuideLibrary
import org.opensources.pokmaps.domain.guide.GuideSpan
import org.opensources.pokmaps.domain.guide.GuideTarget
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class GuideScreenTest {
    @get:Rule val compose = createComposeRule()
    private val context: Context = ApplicationProvider.getApplicationContext()
    private val actions = mutableListOf<GuideAction>()

    private fun show(state: GuideUiState) {
        compose.setContent {
            GuideScreen(state, { actions += it }, GuideLinks({}, {}, {}))
        }
    }

    @Test
    fun roamerArticlePresentsTheVersionRoamerWithoutTracking() {
        val roamers = GuideArticle(
            "hoenn-roamers",
            "Errants",
            GuideCategory.SIDE_QUEST,
            listOf(listOf(GuideSpan("Texte"))),
            381,
            emptyList()
        )
        show(
            GuideUiState(
                loading = false,
                library = GuideLibrary(FakeGameDao.RUBY, listOf(roamers)),
                category = GuideCategory.SIDE_QUEST,
                articleId = roamers.id
            )
        )
        compose.onNode(hasText(context.getString(R.string.guide_roamer_latios))).assertExists()
        compose.onNode(hasText(context.getString(R.string.guide_roamer_latias))).assertDoesNotExist()
        compose.onNode(hasText(context.getString(R.string.guide_roamer_level, 40))).assertExists()
        compose.onNode(hasText(context.getString(R.string.guide_roamer_area_hoenn))).assertExists()
    }

    @Test
    fun secretBaseLinkShowsItsEntranceOnTheMap() {
        val bases = GuideArticle(
            "hoenn-secret-bases",
            "Bases",
            GuideCategory.TIP,
            listOf(listOf(GuideSpan("Route 111 : "), GuideSpan("Base Secrète (arbre 1)", GuideTarget.SecretBase(7)))),
            263,
            emptyList()
        )
        var mapShown = false
        compose.setContent {
            GuideScreen(
                GuideUiState(
                    loading = false,
                    library = GuideLibrary(FakeGameDao.RUBY, listOf(bases)),
                    category = GuideCategory.TIP,
                    articleId = bases.id
                ),
                { actions += it },
                GuideLinks({}, { mapShown = true }, {})
            )
        }
        compose.onNode(hasText("Base Secrète (arbre 1)", substring = true)).performClick()
        assertEquals(listOf(GuideAction.ShowSecretBase(7)), actions)
        assertTrue(mapShown)
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
    fun achievementCheckboxExistsOnlyWithoutConnectedAccount() {
        val achievement = GuideArticle(
            "ra-1",
            "Objectif",
            GuideCategory.ACHIEVEMENT,
            listOf(listOf(GuideSpan("Condition"))),
            25,
            emptyList(),
            achievementId = 1
        )
        var state by androidx.compose.runtime.mutableStateOf(
            GuideUiState(
                loading = false,
                library = GuideLibrary(FakeGameDao.RED, listOf(achievement)),
                category = GuideCategory.ACHIEVEMENT,
                articleId = "ra-1"
            )
        )
        compose.setContent { GuideScreen(state, { actions += it }, GuideLinks({}, {}, {})) }
        compose.onNode(isToggleable()).performClick()
        assertEquals(listOf(GuideAction.Complete("ra-1", true)), actions)
        compose.runOnIdle {
            state = state.copy(
                library = state.library?.copy(
                    retro = org.opensources.pokmaps.domain.guide.RetroProgress(username = "Joueur")
                )
            )
        }
        compose.onNode(isToggleable()).assertDoesNotExist()
        compose.onAllNodes(hasText("Listes officielles", substring = true)).assertCountEquals(0)
    }

    @Test
    fun relatedTrophyOpensTheObjectiveAndChapterHasNoCompletionCheckbox() {
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
        compose.onNode(isToggleable()).assertDoesNotExist()
        assertEquals(listOf(GuideAction.Article("ra-1")), actions)
    }

    @Test
    fun openingAnArticleNeverHashesTheLibrary() {
        val chapter = GuideArticle(
            "chapter",
            "Étape test",
            GuideCategory.WALKTHROUGH,
            listOf(listOf(GuideSpan("Paragraphe"))),
            25,
            emptyList()
        )
        val articles = HashCountingList(listOf(chapter))
        var state by androidx.compose.runtime.mutableStateOf(
            GuideUiState(
                loading = false,
                library = GuideLibrary(FakeGameDao.RED, articles),
                category = GuideCategory.WALKTHROUGH
            )
        )
        compose.mainClock.autoAdvance = false
        compose.setContent { GuideScreen(state, { actions += it }, GuideLinks({}, {}, {})) }
        compose.runOnIdle { state = state.copy(articleId = "chapter") }
        repeat(ANIMATION_FRAMES) { compose.mainClock.advanceTimeByFrame() }
        compose.mainClock.autoAdvance = true

        compose.onNode(hasText("Paragraphe")).assertExists()
        assertEquals(0, articles.hashes)
    }

    /** Liste dont le hachage, qui parcourt chaque article, se compte. */
    private class HashCountingList(private val items: List<GuideArticle>) : List<GuideArticle> by items {
        var hashes = 0

        override fun equals(other: Any?): Boolean = items == other

        override fun hashCode(): Int {
            hashes++
            return items.hashCode()
        }
    }

    private companion object {
        const val ANIMATION_FRAMES = 40
    }
}

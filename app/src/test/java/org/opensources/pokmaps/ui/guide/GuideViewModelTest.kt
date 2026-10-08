package org.opensources.pokmaps.ui.guide

import androidx.lifecycle.SavedStateHandle
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.domain.guide.GuideArticle
import org.opensources.pokmaps.domain.guide.GuideCategory
import org.opensources.pokmaps.domain.guide.GuideLibrary
import org.opensources.pokmaps.domain.guide.GuideProgress
import org.opensources.pokmaps.domain.guide.GuideSpan
import org.opensources.pokmaps.domain.guide.GuideTarget
import org.opensources.pokmaps.domain.usecase.Guides
import org.opensources.pokmaps.domain.usecase.MapRequest
import org.opensources.pokmaps.domain.usecase.MapRequests
import org.opensources.pokmaps.ui.MainDispatcherRule

class GuideViewModelTest {
    @get:Rule val mainDispatcher = MainDispatcherRule()

    @Test
    fun emptyLibraryIsContentAndFailureCanBeRetried() = runTest {
        val guides = MemoryGuides()
        guides.failing = true
        val model = GuideViewModel(SavedStateHandle(), guides, { null }, MapRequests())
        assertTrue(model.state.value.failed)
        guides.failing = false
        model.onAction(GuideAction.Retry)
        assertFalse(model.state.value.failed)
        assertFalse(model.state.value.loading)
        assertTrue(model.state.value.categories.isEmpty())
    }

    @Test
    fun navigationIsRestoredSeparatelyForEachGame() = runTest {
        val guides = MemoryGuides()
        guides.value.value = GuideLibrary(FakeGameDao.RED, listOf(article("red"))) to GuideProgress()
        val model = GuideViewModel(SavedStateHandle(), guides, { null }, MapRequests())
        model.onAction(GuideAction.Article("red"))
        assertEquals(GuideCategory.TIP, model.state.value.category)
        guides.value.value = GuideLibrary(FakeGameDao.BLUE, listOf(article("blue"))) to GuideProgress()
        assertEquals(null, model.state.value.articleId)
        model.onAction(GuideAction.Article("blue"))
        guides.value.value = GuideLibrary(FakeGameDao.RED, listOf(article("red"))) to GuideProgress()
        assertEquals("red", model.state.value.articleId)
    }

    @Test
    fun previewFailureIsVisibleAndMapRequestIsExplicit() = runTest {
        val maps = MapRequests()
        val model = GuideViewModel(SavedStateHandle(), MemoryGuides(), { error("Fiche illisible") }, maps)
        model.onAction(GuideAction.Preview(GuideTarget.Pokemon(25)))
        assertTrue(model.state.value.previewFailed)
        assertFalse(model.state.value.previewLoading)
        model.onAction(GuideAction.ShowPlace("route-1"))
        assertEquals(MapRequest.OpenPlace("route-1"), maps.pending.value)
        assertEquals(null, model.state.value.previewTarget)
        model.onAction(GuideAction.ClosePreview)
        assertEquals(null, model.state.value.previewTarget)
    }

    @Test
    fun returningFromRelatedAchievementRestoresTheChapter() = runTest {
        val chapter = article("chapter").copy(category = GuideCategory.WALKTHROUGH, relatedIds = setOf("ra-1"))
        val achievement = article("ra-1").copy(category = GuideCategory.ACHIEVEMENT, achievementId = 1)
        val guides = MemoryGuides()
        guides.value.value = GuideLibrary(FakeGameDao.RED, listOf(chapter, achievement)) to GuideProgress()
        val model = GuideViewModel(SavedStateHandle(), guides, { null }, MapRequests())
        model.onAction(GuideAction.Article("chapter"))
        model.onAction(GuideAction.Article("ra-1"))
        assertEquals(GuideCategory.ACHIEVEMENT, model.state.value.category)
        model.onAction(GuideAction.Back)
        assertEquals("chapter", model.state.value.articleId)
        assertEquals(GuideCategory.WALKTHROUGH, model.state.value.category)
    }

    @Test
    fun writeFailureLeavesCompletionUntouched() = runTest {
        val guides = MemoryGuides()
        val achievement = article("ra-1").copy(category = GuideCategory.ACHIEVEMENT, achievementId = 1)
        guides.value.value = GuideLibrary(FakeGameDao.RED, listOf(achievement)) to GuideProgress()
        val model = GuideViewModel(SavedStateHandle(), guides, { null }, MapRequests())
        model.onAction(GuideAction.Complete("ra-1", true))
        assertTrue(model.state.value.writeFailed)
        assertTrue(model.state.value.progress.completed.isEmpty())
    }

    @Test
    fun connectionSelectsOnlyRemoteProgressAndBlocksManualWrites() = runTest {
        val guides = MemoryGuides()
        val articles = listOf(article("ra-1").copy(achievementId = 1), article("ra-2").copy(achievementId = 2))
        val library = GuideLibrary(FakeGameDao.RED, articles)
        val progress = GuideProgress(completed = setOf("ra-1", "ra-2"))
        guides.value.value = library to progress
        val model = GuideViewModel(SavedStateHandle(), guides, { null }, MapRequests())
        assertEquals(2, model.state.value.completedAchievements)
        guides.value.value = library.copy(
            retro = org.opensources.pokmaps.domain.guide.RetroProgress(
                username = "Joueur",
                earned = mapOf(1 to setOf(1))
            )
        ) to progress
        assertEquals(1, model.state.value.completedAchievements)
        model.onAction(GuideAction.Complete("ra-2", true))
        assertFalse(model.state.value.writeFailed)
        guides.value.value = library to progress
        assertEquals(2, model.state.value.completedAchievements)
        model.onAction(GuideAction.Complete("missing", true))
        assertFalse(model.state.value.writeFailed)
    }

    private fun article(id: String) =
        GuideArticle(id, id, GuideCategory.TIP, listOf(listOf(GuideSpan(id))), 25, emptyList())
}

private class MemoryGuides : Guides {
    var failing = false
    val value = MutableStateFlow(GuideLibrary(FakeGameDao.RED, emptyList()) to GuideProgress())
    override fun observe(): Flow<Pair<GuideLibrary, GuideProgress>> = if (failing) {
        flow {
            error("Base illisible")
        }
    } else {
        value
    }
    override suspend fun complete(versionId: Int, id: String, completed: Boolean): Unit = error("Écriture impossible")
}

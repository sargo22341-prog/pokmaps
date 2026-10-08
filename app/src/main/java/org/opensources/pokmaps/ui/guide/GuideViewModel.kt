package org.opensources.pokmaps.ui.guide

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import org.opensources.pokmaps.domain.guide.GuideArticle
import org.opensources.pokmaps.domain.guide.GuideCategory
import org.opensources.pokmaps.domain.guide.GuideLibrary
import org.opensources.pokmaps.domain.guide.GuideProgress
import org.opensources.pokmaps.domain.guide.GuideTarget
import org.opensources.pokmaps.domain.usecase.GuidePreview
import org.opensources.pokmaps.domain.usecase.GuidePreviewUseCase
import org.opensources.pokmaps.domain.usecase.GuideUseCase
import org.opensources.pokmaps.domain.usecase.Guides
import org.opensources.pokmaps.domain.usecase.MapRequest
import org.opensources.pokmaps.domain.usecase.MapRequests

data class GuideUiState(
    val loading: Boolean = true,
    val failed: Boolean = false,
    val library: GuideLibrary? = null,
    val progress: GuideProgress = GuideProgress(),
    val category: GuideCategory? = null,
    val articleId: String? = null,
    val previewTarget: GuideTarget? = null,
    val preview: GuidePreview? = null,
    val previewLoading: Boolean = false,
    val previewFailed: Boolean = false,
    val writeFailed: Boolean = false
) {
    val article: GuideArticle? = library?.articles?.firstOrNull { it.id == articleId }
    val articles: List<GuideArticle> = library?.articles.orEmpty().filter { it.category == category }
    val related: List<GuideArticle> = library?.articles.orEmpty().filter { it.id in article?.relatedIds.orEmpty() }
        .sortedByDescending { it.missable }
    val relatedMissable: Int = related.count { it.missable }
    val categories: List<GuideCategory> = GuideCategory.entries.filter { category ->
        library?.articles.orEmpty().any { it.category == category }
    }
    val earned: Set<Int> = library?.retro?.earned?.get(library.game.versionId).orEmpty()
    val hardcore: Set<Int> = library?.retro?.hardcore?.get(library.game.versionId).orEmpty()
    val achievements: List<GuideArticle> = library?.articles.orEmpty().filter { it.achievementId != null }
    val earnedCount: Int = achievements.count { it.achievementId in earned }
    val manuallyCompleted: Int = achievements.count { it.id in progress.completed }
    val captureCounts: Map<String, Int> = library?.articles.orEmpty().associate {
        it.id to if (it.unownGoal) {
            library?.unown.orEmpty().size
        } else {
            (
                it.captureGoal?.count(library?.caught.orEmpty())
                    ?: it.captureIds.count { id -> id in library?.caught.orEmpty() }
                )
        }
    }
    val captureTotals: Map<String, Int> = library?.articles.orEmpty().associate {
        it.id to if (it.unownGoal) 26 else (it.captureGoal?.total ?: it.captureIds.size)
    }
}

sealed interface GuideAction {
    data class Category(val category: GuideCategory) : GuideAction
    data class Article(val id: String) : GuideAction
    data object Back : GuideAction
    data class Complete(val id: String, val completed: Boolean) : GuideAction
    data class Preview(val target: GuideTarget) : GuideAction
    data object ClosePreview : GuideAction
    data class ShowPlace(val identifier: String) : GuideAction
    data class ShowObject(val id: Int) : GuideAction
    data class ObserveRoamer(val pokemonId: Int, val place: String?) : GuideAction
    data object Retry : GuideAction
}

@HiltViewModel
class GuideViewModel internal constructor(
    private val saved: SavedStateHandle,
    private val guides: Guides,
    private val preview: suspend (GuideTarget) -> GuidePreview?,
    private val mapRequests: MapRequests
) : ViewModel() {
    @Inject
    constructor(saved: SavedStateHandle, guides: GuideUseCase, preview: GuidePreviewUseCase, maps: MapRequests) :
        this(saved, guides, { preview(it) }, maps)

    private val mutableState = MutableStateFlow(GuideUiState())
    val state: StateFlow<GuideUiState> = mutableState.asStateFlow()
    private var loadJob: Job? = null
    private var previewJob: Job? = null

    init {
        load()
    }

    private fun load() {
        loadJob?.cancel()
        loadJob = viewModelScope.launch {
            attempt(onError = { mutableState.update { it.copy(loading = false, failed = true) } }) {
                guides.observe().collect { (library, progress) ->
                    val changed = state.value.library?.game?.versionId != library.game.versionId
                    if (changed) previewJob?.cancel()
                    mutableState.update {
                        GuideUiState(
                            loading = false,
                            library = library,
                            progress = progress,
                            category = if (changed) {
                                saved.get<String>("$CATEGORY${library.game.versionId}")
                                    ?.let { name ->
                                        GuideCategory.entries.firstOrNull { category -> category.name == name }
                                    }
                            } else {
                                it.category
                            },
                            articleId = if (changed) {
                                saved.get<String>("$ARTICLE${library.game.versionId}")
                                    ?.takeIf { id -> library.articles.any { article -> article.id == id } }
                            } else {
                                it.articleId
                            },
                            previewTarget = if (changed) null else it.previewTarget,
                            preview = if (changed) null else it.preview,
                            previewLoading = !changed && it.previewLoading,
                            previewFailed = !changed && it.previewFailed
                        )
                    }
                }
            }
        }
    }

    fun onAction(action: GuideAction) {
        when (action) {
            is GuideAction.Category -> select(action.category, null)

            is GuideAction.Article -> select(state.value.category, action.id)

            GuideAction.Back -> back()

            is GuideAction.Complete -> write { version -> guides.complete(version, action.id, action.completed) }

            is GuideAction.ObserveRoamer -> write { version ->
                guides.observeRoamer(version, action.pokemonId, action.place)
            }

            is GuideAction.Preview -> openPreview(action.target)

            GuideAction.ClosePreview -> closePreview()

            is GuideAction.ShowPlace -> {
                closePreview()
                mapRequests.send(MapRequest.OpenPlace(action.identifier))
            }

            is GuideAction.ShowObject -> {
                closePreview()
                mapRequests.send(MapRequest.FocusObject(action.id))
            }

            GuideAction.Retry -> {
                mutableState.update { it.copy(loading = true, failed = false) }
                load()
            }
        }
    }

    private fun select(category: GuideCategory?, articleId: String?, rememberPrevious: Boolean = true) {
        val version = state.value.library?.game?.versionId ?: return
        val article = state.value.library?.articles?.firstOrNull { it.id == articleId }
        val selectedCategory = article?.category ?: category
        if (rememberPrevious) {
            val previous = "${state.value.category?.name.orEmpty()}|${state.value.articleId.orEmpty()}"
            val history = saved.get<ArrayList<String>>("$HISTORY$version").orEmpty()
            saved["$HISTORY$version"] = ArrayList((history + previous).takeLast(MAX_HISTORY))
        }
        saved["$CATEGORY$version"] = selectedCategory?.name
        saved["$ARTICLE$version"] = article?.id
        closePreview()
        mutableState.update { it.copy(category = selectedCategory, articleId = article?.id) }
    }

    private fun back() {
        val version = state.value.library?.game?.versionId ?: return
        val history = saved.get<ArrayList<String>>("$HISTORY$version").orEmpty()
        val previous = history.lastOrNull()?.split("|", limit = 2)
        saved["$HISTORY$version"] = ArrayList(history.dropLast(1))
        val category = previous?.firstOrNull()?.let { name -> GuideCategory.entries.firstOrNull { it.name == name } }
        select(category, previous?.getOrNull(1)?.takeIf { it.isNotEmpty() }, rememberPrevious = false)
    }

    private fun openPreview(target: GuideTarget) {
        previewJob?.cancel()
        mutableState.update {
            it.copy(previewTarget = target, preview = null, previewLoading = true, previewFailed = false)
        }
        previewJob = viewModelScope.launch {
            attempt(onError = { mutableState.update { it.copy(previewLoading = false, previewFailed = true) } }) {
                val result = preview(target)
                mutableState.update { it.copy(preview = result, previewLoading = false) }
            }
        }
    }

    private fun closePreview() {
        previewJob?.cancel()
        mutableState.update { it.copy(previewTarget = null, preview = null, previewLoading = false) }
    }

    private fun write(block: suspend (Int) -> Unit) {
        val version = state.value.library?.game?.versionId ?: return
        viewModelScope.launch {
            attempt(onError = { mutableState.update { it.copy(writeFailed = true) } }) { block(version) }
        }
    }

    private suspend fun attempt(onError: () -> Unit, block: suspend () -> Unit) {
        try {
            block()
        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (_: Exception) {
            onError()
        }
    }

    private companion object {
        const val CATEGORY = "guide_category"
        const val ARTICLE = "guide_article"
        const val HISTORY = "guide_history"
        const val MAX_HISTORY = 256
    }
}

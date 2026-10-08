package org.opensources.pokmaps.ui.guide

import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.GuideArticle
import org.opensources.pokmaps.domain.guide.GuideCategory
import org.opensources.pokmaps.domain.guide.GuideTarget
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.ui.common.LocalAnimatedPlaces
import org.opensources.pokmaps.ui.common.PokemonSprite
import org.opensources.pokmaps.ui.common.SheetPlaceholder
import org.opensources.pokmaps.ui.common.SpriteSize

data class GuideLinks(val open: (GuideTarget) -> Unit, val showMap: () -> Unit, val openPokedex: () -> Unit)

@Composable
fun GuideRoute(links: GuideLinks, modifier: Modifier = Modifier, viewModel: GuideViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    GuideScreen(
        state,
        onAction = { action ->
            viewModel.onAction(action)
            if (action is GuideAction.ShowPlace || action is GuideAction.ShowObject) links.showMap()
        },
        links = links,
        modifier = modifier,
        breedingTool = { BreedingRoute(onPreview = { viewModel.onAction(GuideAction.Preview(it)) }) },
        friendshipTool = { FriendshipRoute(state.library?.game?.versionId == 6) }
    )
}

@Composable
fun GuideScreen(
    state: GuideUiState,
    onAction: (GuideAction) -> Unit,
    links: GuideLinks,
    modifier: Modifier = Modifier,
    breedingTool: @Composable () -> Unit = {},
    friendshipTool: @Composable () -> Unit = {}
) {
    BackHandler(state.category != null && state.previewTarget == null) { onAction(GuideAction.Back) }
    if (state.loading || state.failed || state.library == null) {
        Column(modifier.fillMaxSize()) {
            if (state.failed) {
                Button(onClick = {
                    onAction(GuideAction.Retry)
                }) { Text(stringResource(R.string.guide_retry)) }
            }
            SheetPlaceholder(state.loading, stringResource(R.string.guide_empty), failed = state.failed)
        }
        return
    }
    AnimatedContent(targetState = state, contentKey = { it.category to it.articleId }, label = "guide") { screen ->
        val article = screen.article
        if (article == null) {
            GuideIndex(screen, onAction, modifier)
        } else {
            GuideArticleContent(screen, article, onAction, links, modifier, breedingTool, friendshipTool)
        }
    }
    if (state.previewTarget != null) GuidePreviewSheet(state, onAction, links)
}

@Composable
private fun GuideIndex(state: GuideUiState, onAction: (GuideAction) -> Unit, modifier: Modifier) {
    LazyColumn(modifier.fillMaxSize().padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item("header") { GuideHeading(state, onAction) }
        if (state.category == null) {
            items(state.categories, key = { it.name }) { category ->
                Card(onClick = { onAction(GuideAction.Category(category)) }, modifier = Modifier.fillMaxWidth()) {
                    Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                        PokemonSprite(category.pokemonId(), SpritePlace.POKEMON_SHEET, SpriteSize.LIST, null)
                        Column(Modifier.weight(1f)) {
                            Text(stringResource(category.label()), style = MaterialTheme.typography.titleLarge)
                            Text(stringResource(category.description()), style = MaterialTheme.typography.bodyMedium)
                        }
                    }
                }
            }
        } else {
            items(state.articles, key = { it.id }) { article -> GuideArticleCard(state, article, onAction) }
            if (state.articles.isEmpty()) item("empty") { Text(stringResource(R.string.guide_empty)) }
        }
    }
}

@Composable
internal fun GuideHeading(state: GuideUiState, onAction: (GuideAction) -> Unit) {
    Column(Modifier.padding(vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        if (state.category != null) {
            TextButton(onClick = { onAction(GuideAction.Back) }) { Text(stringResource(R.string.back)) }
        }
        Text(
            stringResource(state.category?.label() ?: R.string.nav_guides),
            style = MaterialTheme.typography.headlineMedium
        )
        state.library?.game?.let { Text(stringResource(R.string.game_name, it.name)) }
        if (state.category == GuideCategory.ACHIEVEMENT) {
            Text(
                stringResource(
                    if (state.automaticAchievements) R.string.retro_automatic_totals else R.string.retro_manual_totals,
                    state.completedAchievements,
                    state.achievements.size
                )
            )
        }
        if (state.writeFailed) Text(stringResource(R.string.guide_save_error), color = MaterialTheme.colorScheme.error)
    }
}

@Composable
internal fun GuideArticleCard(state: GuideUiState, article: GuideArticle, onAction: (GuideAction) -> Unit) {
    Card(onClick = { onAction(GuideAction.Article(article.id)) }, modifier = Modifier.fillMaxWidth()) {
        Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            PokemonSprite(
                article.pokemonId,
                SpritePlace.POKEMON_SHEET,
                SpriteSize.LIST,
                null,
                shiny = article.shiny,
                animated = article.shiny || SpritePlace.POKEMON_SHEET in LocalAnimatedPlaces.current
            )
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(article.title, style = MaterialTheme.typography.titleMedium)
                if (article.achievementId != null) {
                    Text(article.summary, maxLines = 2, overflow = androidx.compose.ui.text.style.TextOverflow.Ellipsis)
                }
                if (article.missable) {
                    Text(
                        stringResource(R.string.guide_missable),
                        color = MaterialTheme.colorScheme.error
                    )
                }
                if (article.achievementId != null && !state.automaticAchievements &&
                    article.id in state.progress.completed
                ) {
                    Text(stringResource(R.string.guide_completed))
                }
                RetroAchievementStatus(state, article)
                if (article.captureIds.isNotEmpty() || article.unownGoal) {
                    Text(
                        stringResource(
                            if (article.unownGoal) R.string.guide_unown_progress else R.string.guide_capture_progress,
                            state.captureCounts[article.id] ?: 0,
                            state.captureTotals[article.id] ?: 0
                        )
                    )
                }
            }
        }
    }
}

internal fun GuideCategory.label(): Int = when (this) {
    GuideCategory.WALKTHROUGH -> R.string.guide_walkthrough
    GuideCategory.SIDE_QUEST -> R.string.guide_side_quests
    GuideCategory.TIP -> R.string.guide_tips
    GuideCategory.GLITCH -> R.string.guide_glitches
    GuideCategory.CALENDAR -> R.string.guide_calendar
    GuideCategory.ACHIEVEMENT -> R.string.guide_achievements
}

private fun GuideCategory.description(): Int = when (this) {
    GuideCategory.WALKTHROUGH -> R.string.guide_walkthrough_description
    GuideCategory.SIDE_QUEST -> R.string.guide_side_quests_description
    GuideCategory.TIP -> R.string.guide_tips_description
    GuideCategory.GLITCH -> R.string.guide_glitches_description
    GuideCategory.CALENDAR -> R.string.guide_calendar_description
    GuideCategory.ACHIEVEMENT -> R.string.guide_achievements_description
}

private fun GuideCategory.pokemonId(): Int = when (this) {
    GuideCategory.WALKTHROUGH -> 25
    GuideCategory.SIDE_QUEST -> 145
    GuideCategory.TIP -> 133
    GuideCategory.GLITCH -> 132
    GuideCategory.CALENDAR -> 35
    GuideCategory.ACHIEVEMENT -> 149
}

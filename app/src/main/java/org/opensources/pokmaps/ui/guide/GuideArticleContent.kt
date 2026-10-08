package org.opensources.pokmaps.ui.guide

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Checkbox
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.LinkAnnotation
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.TextLinkStyles
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.withLink
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.guide.GuideArticle
import org.opensources.pokmaps.domain.guide.GuideSpan
import org.opensources.pokmaps.domain.guide.GuideTarget
import org.opensources.pokmaps.domain.model.SpritePlace
import org.opensources.pokmaps.ui.common.PokemonSprite
import org.opensources.pokmaps.ui.common.SpriteSize

@Composable
internal fun GuideArticleContent(
    state: GuideUiState,
    article: GuideArticle,
    onAction: (GuideAction) -> Unit,
    links: GuideLinks,
    onOpenSource: (String) -> Unit,
    modifier: Modifier,
    breedingTool: @Composable () -> Unit,
    friendshipTool: @Composable () -> Unit
) {
    var relatedVisible by remember(article.id) { mutableStateOf(false) }
    LazyColumn(
        modifier.padding(horizontal = 20.dp),
        verticalArrangement = Arrangement.spacedBy(20.dp)
    ) {
        item("header") {
            GuideArticleHeader(state, article, onAction, links, { relatedVisible = !relatedVisible })
        }
        if (relatedVisible) {
            items(state.related, key = { "related-${it.id}" }) { related ->
                GuideArticleCard(state, related, onAction)
            }
        }
        items(article.paragraphs.indices.toList(), key = { "paragraph-$it" }) { index ->
            GuideParagraph(article.paragraphs[index]) { onAction(GuideAction.Preview(it)) }
        }
        if (article.id == "johto-roamers") item("roamers") { RoamerTracker(state, onAction) }
        if (article.id == "breeding") item("breeding") { breedingTool() }
        if (article.id == "friendship") item("friendship") { friendshipTool() }
        item("sources") {
            HorizontalDivider()
            Text(stringResource(R.string.guide_sources), style = MaterialTheme.typography.titleSmall)
            article.sources.forEachIndexed { index, source ->
                TextButton(onClick = { onOpenSource(source) }) {
                    Text(stringResource(R.string.guide_source_number, index + 1, article.sourceHosts[index]))
                }
            }
        }
    }
}

@Composable
private fun GuideArticleHeader(
    state: GuideUiState,
    article: GuideArticle,
    onAction: (GuideAction) -> Unit,
    links: GuideLinks,
    onRelated: () -> Unit
) {
    GuideHeading(state, onAction)
    Text(article.title, style = MaterialTheme.typography.headlineSmall)
    if (state.related.isNotEmpty()) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
            TextButton(onClick = onRelated) {
                Icon(painterResource(R.drawable.ic_star), contentDescription = null)
                Text(stringResource(R.string.guide_related_achievements, state.related.size, state.relatedMissable))
            }
        }
    }
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
        PokemonSprite(article.pokemonId, SpritePlace.POKEMON_SHEET, SpriteSize.HEADER, article.title)
    }
    GuideCompletion(article, state, onAction)
    GuideCaptureProgress(article, state, links.openPokedex)
}

@Composable
internal fun GuideParagraph(spans: List<GuideSpan>, onOpen: (GuideTarget) -> Unit) {
    val linkStyle =
        TextLinkStyles(
            style = SpanStyle(color = MaterialTheme.colorScheme.tertiary, textDecoration = TextDecoration.Underline)
        )
    val text = buildAnnotatedString {
        spans.forEachIndexed { index, span ->
            val target = span.target
            if (target == null) {
                append(span.text)
            } else {
                withLink(LinkAnnotation.Clickable("$index", linkStyle) { onOpen(target) }) { append(span.text) }
            }
        }
    }
    Text(text, style = MaterialTheme.typography.bodyLarge)
}

@Composable
private fun GuideCompletion(article: GuideArticle, state: GuideUiState, onAction: (GuideAction) -> Unit) {
    Column {
        if (article.missable) Text(stringResource(R.string.guide_missable), color = MaterialTheme.colorScheme.error)
        if (article.achievementId != null) {
            Text(stringResource(R.string.retro_points, article.points, article.achievementId))
            RetroAchievementStatus(state, article)
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            Checkbox(
                checked = article.id in state.progress.completed,
                onCheckedChange = { onAction(GuideAction.Complete(article.id, it)) }
            )
            Text(
                stringResource(
                    if (article.achievementId ==
                        null
                    ) {
                        R.string.guide_mark_completed
                    } else {
                        R.string.retro_manual
                    }
                )
            )
        }
    }
}

@Composable
internal fun GuideCaptureProgress(article: GuideArticle, state: GuideUiState, onPokedex: () -> Unit) {
    if (article.captureIds.isEmpty() && !article.unownGoal) return
    val count = state.captureCounts[article.id] ?: 0
    TextButton(onClick = onPokedex) {
        Text(
            stringResource(
                if (article.unownGoal) R.string.guide_unown_progress else R.string.guide_capture_progress,
                count,
                state.captureTotals[article.id] ?: 0
            )
        )
    }
    Text(stringResource(R.string.retro_collection_hint), style = MaterialTheme.typography.bodySmall)
}

@Composable
internal fun RetroAchievementStatus(state: GuideUiState, article: GuideArticle) {
    if (article.achievementId in state.earned) {
        Text(
            stringResource(
                if (article.achievementId in
                    state.hardcore
                ) {
                    R.string.retro_hardcore
                } else {
                    R.string.retro_earned
                }
            ),
            color = MaterialTheme.colorScheme.primary
        )
    }
}

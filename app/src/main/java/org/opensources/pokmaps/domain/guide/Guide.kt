package org.opensources.pokmaps.domain.guide

import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.pokemon.UnownForm

enum class GuideCategory { WALKTHROUGH, SIDE_QUEST, TIP, GLITCH, CALENDAR, ACHIEVEMENT }

sealed interface GuideTarget {
    data class Pokemon(val id: Int) : GuideTarget
    data class Place(val identifier: String) : GuideTarget
    data class Item(val identifier: String) : GuideTarget
    data class Character(val id: Int) : GuideTarget
}

data class GuideSpan(val text: String, val target: GuideTarget? = null)

data class GuideArticle(
    val id: String,
    val title: String,
    val category: GuideCategory,
    val paragraphs: List<List<GuideSpan>>,
    val pokemonId: Int,
    val sources: List<String>,
    val relatedIds: Set<String> = emptySet(),
    val missable: Boolean = false,
    val captureIds: Set<Int> = emptySet(),
    val achievementId: Int? = null,
    val points: Int = 0,
    val captureGoal: CaptureGoal? = null
) {
    val sourceHosts: List<String> = sources.map { java.net.URI(it).host }
    val unownGoal: Boolean = achievementId in setOf(5091, 5117, 5955)
}

data class GuideLibrary(
    val game: Game,
    val articles: List<GuideArticle>,
    val caught: Set<Int> = emptySet(),
    val retro: RetroProgress = RetroProgress(),
    val unown: Set<UnownForm> = emptySet()
) {
    init {
        require(articles.size <= 500)
        require(articles.map { it.id }.distinct().size == articles.size)
        require(articles.all { article -> article.relatedIds.all { id -> articles.any { it.id == id } } })
    }
}

data class RoamerObservation(val pokemonId: Int, val place: String)

data class GuideProgress(val completed: Set<String> = emptySet(), val roamers: List<RoamerObservation> = emptyList())

/** Les balises sont validées une fois lors du chargement, avant le rendu. */
fun parseGuideText(text: String, resolve: (String, String) -> GuideTarget): List<List<GuideSpan>> {
    require(text.length <= 30_000)
    return text.split("\n\n").map { paragraph ->
        val spans = mutableListOf<GuideSpan>()
        var start = 0
        for (match in LINK.findAll(paragraph)) {
            if (match.range.first > start) spans += GuideSpan(paragraph.substring(start, match.range.first))
            spans += GuideSpan(match.groupValues[3], resolve(match.groupValues[1], match.groupValues[2]))
            start = match.range.last + 1
        }
        if (start < paragraph.length) spans += GuideSpan(paragraph.substring(start))
        require(spans.none { "[[" in it.text || "]]" in it.text }) { "Lien de guide mal formé : $paragraph" }
        spans.toList()
    }
}

private val LINK = Regex("""\[\[(pokemon|place|item|character):([^|\]]+)\|([^\]]+)]]""")

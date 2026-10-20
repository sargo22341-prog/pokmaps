package org.opensources.pokmaps.data.guide

import org.opensources.pokmaps.R.string
import org.opensources.pokmaps.domain.guide.Gen4CaptureGoals
import org.opensources.pokmaps.domain.guide.GuideCategory
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.model.VersionGroup

internal fun sinnohGuides(game: Game): List<GuideDefinition> = SinnohGuides(game).articles()

private class SinnohGuides(private val game: Game) {
    private val sources = sinnohGuideSources(game)
    private val platinum = game.versionGroup == VersionGroup.PLATINUM

    fun articles(): List<GuideDefinition> = walkthrough() + sideQuests() + calendar() + collections()

    private fun walkthrough(): List<GuideDefinition> = listOf(
        article(
            "start",
            string.guide_sinnoh_start_title,
            text(string.guide_sinnoh_start_dp_text, string.guide_sinnoh_start_pt_text),
            387
        ),
        article("oreburgh", string.guide_sinnoh_oreburgh_title, string.guide_sinnoh_oreburgh_text, 408),
        article("eterna", string.guide_sinnoh_eterna_title, string.guide_sinnoh_eterna_text, 407),
        article(
            "hearthome",
            string.guide_sinnoh_hearthome_title,
            text(string.guide_sinnoh_hearthome_dp_text, string.guide_sinnoh_hearthome_pt_text),
            429
        ),
        article("veilstone", string.guide_sinnoh_veilstone_title, string.guide_sinnoh_veilstone_text, 448),
        article(
            "pastoria",
            string.guide_sinnoh_pastoria_title,
            text(string.guide_sinnoh_pastoria_dp_text, string.guide_sinnoh_pastoria_pt_text),
            419
        ),
        article(
            "canalave",
            string.guide_sinnoh_canalave_title,
            text(string.guide_sinnoh_canalave_dp_text, string.guide_sinnoh_canalave_pt_text),
            411
        ),
        article("snowpoint", string.guide_sinnoh_snowpoint_title, string.guide_sinnoh_snowpoint_text, 460),
        article(
            "summit",
            string.guide_sinnoh_summit_title,
            text(string.guide_sinnoh_summit_dp_text, string.guide_sinnoh_summit_pt_text),
            game.mascotPokemonId
        ),
        article("league", string.guide_sinnoh_league_title, string.guide_sinnoh_league_text, 445),
        article(
            "national",
            string.guide_sinnoh_national_title,
            text(string.guide_sinnoh_national_dp_text, string.guide_sinnoh_national_pt_text),
            490
        ),
        article(
            "postgame",
            string.guide_sinnoh_postgame_title,
            text(string.guide_sinnoh_postgame_dp_text, string.guide_sinnoh_postgame_pt_text),
            485
        )
    )

    private fun sideQuests(): List<GuideDefinition> = listOf(
        article(
            "fossils",
            string.guide_sinnoh_fossils_title,
            text(string.guide_sinnoh_fossils_dp_text, string.guide_sinnoh_fossils_pt_text),
            408,
            GuideCategory.SIDE_QUEST
        ),
        article(
            "gifts",
            string.guide_sinnoh_gifts_title,
            text(string.guide_sinnoh_gifts_dp_text, string.guide_sinnoh_gifts_pt_text),
            447,
            GuideCategory.SIDE_QUEST
        ),
        article(
            "honey",
            string.guide_sinnoh_honey_title,
            string.guide_sinnoh_honey_text,
            446,
            GuideCategory.SIDE_QUEST
        ),
        article(
            "rotom",
            string.guide_sinnoh_rotom_title,
            text(string.guide_sinnoh_rotom_dp_text, string.guide_sinnoh_rotom_pt_text),
            479,
            GuideCategory.SIDE_QUEST
        ),
        article(
            "events",
            string.guide_sinnoh_events_title,
            string.guide_sinnoh_events_text,
            486,
            GuideCategory.SIDE_QUEST
        ),
        article("capture", string.guide_sinnoh_capture_title, string.guide_sinnoh_capture_text, 425, GuideCategory.TIP),
        article(
            "bugs",
            text(string.guide_sinnoh_bugs_dp_title, string.guide_sinnoh_bugs_pt_title),
            text(string.guide_sinnoh_bugs_dp_text, string.guide_sinnoh_bugs_pt_text),
            479,
            GuideCategory.GLITCH
        )
    )

    private fun calendar(): List<GuideDefinition> = listOf(
        article("clock", string.guide_sinnoh_clock_title, string.guide_sinnoh_clock_text, 163, GuideCategory.CALENDAR),
        article(
            "friday",
            string.guide_sinnoh_friday_title,
            text(string.guide_sinnoh_friday_dp_text, string.guide_sinnoh_friday_pt_text),
            425,
            GuideCategory.CALENDAR
        ),
        article("daily", string.guide_sinnoh_daily_title, string.guide_sinnoh_daily_text, 315, GuideCategory.CALENDAR),
        article(
            "weekend",
            string.guide_sinnoh_weekend_title,
            text(string.guide_sinnoh_weekend_dp_text, string.guide_sinnoh_weekend_pt_text),
            398,
            GuideCategory.CALENDAR
        )
    )

    private fun collections(): List<GuideDefinition> = listOf(
        article(
            "regional-collection",
            string.guide_sinnoh_regional_collection_title,
            string.guide_sinnoh_collection_text,
            387,
            GuideCategory.SIDE_QUEST
        )
            .copy(captureGoal = Gen4CaptureGoals.forVersion(game.versionId, national = false)),
        article(
            "national-collection",
            string.guide_sinnoh_national_collection_title,
            string.guide_sinnoh_collection_text,
            493,
            GuideCategory.SIDE_QUEST
        )
            .copy(captureGoal = Gen4CaptureGoals.forVersion(game.versionId, national = true))
    )

    private fun text(diamondPearl: Int, platinum: Int): Int = if (this.platinum) platinum else diamondPearl

    private fun article(
        id: String,
        title: Int,
        text: Int,
        pokemon: Int,
        category: GuideCategory = GuideCategory.WALKTHROUGH
    ): GuideDefinition = GuideDefinition("sinnoh-$id", title, text, category, setOf(game.versionId), pokemon, sources)
}

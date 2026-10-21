package org.opensources.pokmaps.domain.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class RouteEncountersTest {
    private fun encounter(method: String = "walk", vararg keys: String) = Encounter(
        12, "Diamant", 1, "Route", 16, "Roucool", method, method, 1, false,
        2, 4, 20.0, 1, null, null, conditionKeys = keys.toSet()
    )

    @Test
    fun giftsAndEggsHaveTheirOwnListWithoutHidingTheirRequirements() {
        val methods = listOf(
            "gift",
            "gift-egg",
            "pokemon-ranger",
            "colosseum-bonus-disc-jpn",
            "colosseum-bonus-disc-us",
            "pokemon-channel-pal"
        )
        for (method in methods) {
            val gift = encounter(method, "story-progress-national-dex").copy(
                conditions = "Pok\u00e9dex National",
                conditionNames = mapOf("story-progress-national-dex" to "Pok\u00e9dex National")
            )
            assertFalse(RouteEncounterFilter().matches(gift))
            assertFalse(RouteEncounterFilter(roaming = true).matches(gift))
            assertEquals(listOf(gift), RouteEncounterFilter(gifts = true).apply(listOf(gift)))
        }
        assertFalse(RouteEncounterFilter(gifts = true).matches(encounter()))
        assertFalse(RouteEncounterFilter(gifts = true).matches(encounter("npc-trade")))
        assertFalse(RouteEncounterFilter(gifts = true).matches(encounter("roaming-grass")))
    }

    @Test
    fun defaultShowsOrdinaryEncountersWithoutInsertedCartridge() {
        val filter = RouteEncounterFilter()
        assertTrue(filter.matches(encounter()))
        assertTrue(filter.matches(encounter("walk", "slot2-none", "radar-off", "swarm-no")))
        assertFalse(filter.matches(encounter("walk", "slot2-ruby")))
        assertFalse(filter.matches(encounter("walk", "radar-on")))
        assertFalse(filter.matches(encounter("walk", "swarm-yes")))
        assertFalse(filter.matches(encounter("walk", "story-progress-national-dex")))
    }

    @Test
    fun insertedCartridgeReplacesOnlyItsConditionalSlots() {
        for (cartridge in GbaCartridge.entries) {
            val filter = RouteEncounterFilter(cartridge, nationalDex = true)
            assertTrue(filter.matches(encounter()))
            for (candidate in GbaCartridge.entries) {
                assertTrue(filter.matches(encounter("walk", candidate.condition)) == (candidate == cartridge))
            }
        }
    }

    @Test
    fun roamersHaveTheirOwnListAcrossGenerations() {
        for (method in listOf("roaming-grass", "roaming-water")) {
            val roamer = encounter(method, "story-progress-national-dex")
            assertFalse(RouteEncounterFilter().matches(roamer))
            assertTrue(RouteEncounterFilter(roaming = true).matches(roamer))
        }
        assertFalse(RouteEncounterFilter(roaming = true).matches(encounter()))
    }

    @Test
    fun activeSlotsMergeTheirProbabilitiesAndRemoveSelectedLabels() {
        val base = encounter("walk", "radar-off").copy(
            conditionNames = mapOf("radar-off" to "Sans Pokéradar"),
            conditions = "Sans Pokéradar"
        )
        val other = encounter("walk", "slot2-none").copy(
            chance = 10.0,
            conditionNames = mapOf("slot2-none" to "Sans jeu GBA"),
            conditions = "Sans jeu GBA"
        )
        val merged = RouteEncounterFilter().apply(listOf(base, other)).single()
        assertEquals(30.0, requireNotNull(merged.chance), 0.0)
        assertEquals(null, merged.conditions)
        assertTrue(merged.conditionKeys.isEmpty())
    }

    @Test
    fun nationalRadarAndSwarmRespectBothSidesOfTheirConditions() {
        val filter = RouteEncounterFilter(radar = true, swarm = true, nationalDex = true)
        assertTrue(filter.matches(encounter("walk", "radar-on", "swarm-yes", "story-progress-national-dex")))
        assertFalse(filter.matches(encounter("walk", "radar-off")))
        assertFalse(filter.matches(encounter("walk", "swarm-no")))
        assertFalse(filter.matches(encounter("walk", "story-progress-before-national-dex")))
    }
}

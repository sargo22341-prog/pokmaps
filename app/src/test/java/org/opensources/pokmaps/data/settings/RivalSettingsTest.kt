package org.opensources.pokmaps.data.settings

import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test
import org.opensources.pokmaps.domain.map.RivalChoice

class RivalSettingsTest {
    @Test
    fun nothingChosenGivesTheDefaults() = runTest {
        assertEquals(RivalChoice(), RivalSettings(FakeDataStore()).choice("red-blue").first())
    }

    @Test
    fun choicesAreKeptPerVersionGroup() = runTest {
        val settings = RivalSettings(FakeDataStore())
        val yellow = RivalChoice(starterId = 25, wonLabBattle = false, wonRoute22Battle = false)
        settings.set("red-blue", RivalChoice(starterId = 4))
        settings.set("yellow", yellow)
        assertEquals(RivalChoice(starterId = 4), settings.choice("red-blue").first())
        assertEquals(yellow, settings.choice("yellow").first())
        assertEquals(RivalChoice(), settings.choice("gold-silver").first())
    }

    @Test
    fun aStarterCanBeForgotten() = runTest {
        val settings = RivalSettings(FakeDataStore())
        settings.set("emerald", RivalChoice(starterId = 255))
        settings.set("emerald", RivalChoice())
        assertEquals(RivalChoice(), settings.choice("emerald").first())
    }
}

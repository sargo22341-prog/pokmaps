package org.opensources.pokmaps.data.repository

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import kotlinx.coroutines.test.runTest
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.domain.hoenn.ContestCategory
import org.opensources.pokmaps.domain.map.OfferCurrency
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class HoennRepositoryTest {
    private val emerald = FakeGameDao.RED.copy(
        versionId = 9,
        versionIdentifier = "emerald",
        versionGroupId = 6,
        versionGroupIdentifier = "emerald",
        generationId = 3
    )

    private fun catalog(): String = ApplicationProvider.getApplicationContext<Context>().assets
        .open("hoenn.json").bufferedReader().use { it.readText() }

    @Test
    fun bothHoennGroupsKeepBerryPropertiesAndContestCombinations() = runTest {
        val repository = HoennRepository(::catalog)
        for (group in listOf("ruby-sapphire", "emerald")) {
            val content = requireNotNull(repository.content(emerald.copy(versionGroupIdentifier = group)))
            assertEquals(43, content.berries.size)
            assertEquals(354, content.moves.size)
            assertEquals(120, content.decorations.size)
            assertEquals(listOf(10, 0, 0, 0, 0), content.berries.getValue("cheri-berry").flavors)
            assertEquals(ContestCategory.TOUGH, content.moves.getValue(1).category)
            assertEquals(listOf("Groz’Yeux"), content.moves.getValue(23).previous)
            assertEquals(3000, content.decorations.first { it.identifier == "DECOR_SMALL_DESK" }.price)
        }
    }

    @Test
    fun decorationPricesKeepTheirRealCurrency() = runTest {
        val content = requireNotNull(HoennRepository(::catalog).content(emerald))
        val casino = content.sources.filter { it.map == "mauville-city-game-corner" && !it.gift }
        assertEquals(3, casino.size)
        assertTrue(casino.all { it.currency == OfferCurrency.COINS && it.price == 1000 })
        assertTrue(content.sources.any { it.currency == OfferCurrency.BATTLE_POINTS && it.price == 256 })
        assertTrue(content.sources.any { it.currency == OfferCurrency.ASHES && it.price == 8000 })
    }

    @Test
    fun remakesAndOlderGamesDoNotLoadHoennContent() = runTest {
        val repository = HoennRepository { error("Lecture inattendue") }
        assertNull(repository.content(FakeGameDao.RED))
        assertNull(repository.content(emerald.copy(versionGroupIdentifier = "firered-leafgreen")))
    }

    @Test
    fun catalogIsReadOnceAcrossVersions() = runTest {
        var reads = 0
        val repository = HoennRepository {
            reads++
            catalog()
        }
        repository.content(emerald)
        repository.content(emerald.copy(versionGroupIdentifier = "ruby-sapphire"))
        assertEquals(1, reads)
    }

    @Test(expected = IllegalArgumentException::class)
    fun unknownCategoryIsRejectedAtTheBoundary() = runTest {
        val root = JSONObject(catalog())
        root.getJSONObject("groups").getJSONObject("emerald").getJSONArray("moves")
            .getJSONObject(0).put("category", "UNKNOWN")
        HoennRepository { root.toString() }.content(emerald)
    }

    @Test(expected = IllegalStateException::class)
    fun fileFailuresRemainVisible() = runTest {
        HoennRepository { error("Catalogue absent") }.content(emerald)
    }
}

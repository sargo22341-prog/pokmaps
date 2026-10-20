package org.opensources.pokmaps.data.repository

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import kotlinx.coroutines.test.runTest
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.domain.hoenn.ContestCategory
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class SinnohRepositoryTest {
    private val diamond = FakeGameDao.RED.copy(
        versionId = 12,
        versionIdentifier = "diamond",
        versionGroupId = 8,
        versionGroupIdentifier = "diamond-pearl",
        generationId = 4
    )
    private val platinum = diamond.copy(
        versionId = 14,
        versionIdentifier = "platinum",
        versionGroupId = 9,
        versionGroupIdentifier = "platinum"
    )

    private fun catalog(): String = ApplicationProvider.getApplicationContext<Context>().assets
        .open("sinnoh.json").bufferedReader().use { it.readText() }

    @Test
    fun berriesAndSuperContestMovesAreAvailableForEachVersion() = runTest {
        val repository = SinnohRepository(::catalog)
        for (game in listOf(diamond, diamond.copy(versionId = 13, versionIdentifier = "pearl"), platinum)) {
            val content = checkNotNull(repository.content(game))
            assertEquals(64, content.berries.size)
            assertEquals(467, content.moves.size)
            val berry = content.berries.getValue("cheri-berry")
            assertEquals(3, berry.stageHours)
            assertEquals(5, berry.maxYield)
            assertEquals(listOf(10, 0, 0, 0, 0), berry.flavors)
            assertEquals(ContestCategory.TOUGH, content.moves.getValue(1).category)
            assertEquals(3, content.moves.getValue(1).appeal)
        }
    }

    @Test
    fun undergroundKeepsExclusiveUpperPricesAndUnavailableGoods() = runTest {
        val content = checkNotNull(SinnohRepository(::catalog).content(platinum)).underground
        assertEquals(132, content.goods.size)
        assertEquals(27, content.traps.size)
        assertEquals(58, content.mining.size)
        val chair = content.goods.single { it.id == 9 }
        assertEquals(3, chair.price.sphere)
        assertEquals(8, chair.price.minimum)
        assertEquals(10, chair.price.maximumExclusive)
        assertFalse(content.goods.single { it.id == 125 }.available)
        assertFalse(content.goods.single { it.id == 129 }.available)
        assertTrue(content.goods.single { it.id == 118 }.available)
        assertEquals(25, content.mining.single { it.id == 36 }.weights[1])
    }

    @Test
    fun battleSeriesAndHallAreVersionSpecific() = runTest {
        val repository = SinnohRepository(::catalog)
        val dp = checkNotNull(repository.content(diamond)).battles
        val pt = checkNotNull(repository.content(platinum)).battles
        assertNull(dp.frontier)
        assertEquals(950, dp.configurations.size)
        assertEquals(0..99, dp.tower.first().ordinary)
        assertEquals(100..119, dp.tower.first().last)
        assertEquals(setOf(464, 350, 149), dp.trainers[305].map { dp.configurations.getValue(it).species }.toSet())
        val frontier = checkNotNull(pt.frontier)
        assertEquals(0..98, frontier.castle.first().ordinary)
        assertEquals(477, frontier.hall.size)
        assertEquals(1..154, frontier.hallRanks.first())
        assertEquals(1, frontier.level50.first().first)
        assertEquals(351, frontier.openPlayer.first().first)
        assertEquals(100, frontier.level50.first().trainerLimit)
        assertTrue(pt.possibilities(pt.tower.first().ordinary).isNotEmpty())
    }

    @Test
    fun otherGenerationsDoNotOpenTheCatalogAndSinnohReadsOnlyOnce() = runTest {
        var reads = 0
        val repository = SinnohRepository {
            reads += 1
            catalog()
        }
        assertNull(repository.content(FakeGameDao.RED))
        assertEquals(0, reads)
        repository.content(diamond)
        repository.content(platinum)
        assertEquals(1, reads)
    }

    @Test(expected = IllegalArgumentException::class)
    fun unknownContestCategoryIsRejected() = runTest {
        val root = JSONObject(catalog())
        root.getJSONObject("groups").getJSONObject("platinum").getJSONArray("moves")
            .getJSONObject(0).put("category", "UNKNOWN")
        SinnohRepository { root.toString() }.content(platinum)
    }

    @Test(expected = IllegalArgumentException::class)
    fun missingConfigurationsAreRejected() = runTest {
        val root = JSONObject(catalog())
        root.getJSONObject("groups").getJSONObject("platinum").getJSONObject("battles")
            .getJSONArray("sets").remove(0)
        SinnohRepository { root.toString() }.content(platinum)
    }

    @Test(expected = IllegalStateException::class)
    fun readFailuresRemainVisible() = runTest {
        SinnohRepository { error("Catalogue absent") }.content(diamond)
    }
}

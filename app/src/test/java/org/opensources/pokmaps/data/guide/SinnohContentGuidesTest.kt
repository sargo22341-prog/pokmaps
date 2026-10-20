package org.opensources.pokmaps.data.guide

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.R
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.data.repository.SinnohRepository
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class SinnohContentGuidesTest {
    @Test
    fun arcadeRemovesHeldItemsWhileTowerKeepsThem() = runTest {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val content = checkNotNull(SinnohRepository(context).content(FakeGameDao.PLATINUM))
        val row = content.battles.configurations.getValue(1)
        assertTrue(row.item.isNotBlank())
        val tower = configurationParagraph(context, row).joinToString("") { it.text }
        val arcade = configurationParagraph(context, row, keepsItem = false).joinToString("") { it.text }
        assertTrue(tower.contains(row.item))
        assertFalse(arcade.contains(row.item))
        assertTrue(arcade.contains(context.getString(R.string.sinnoh_no_item)))
    }

    @Test
    fun furniturePricesShowTheLastPossibleSizeRatherThanTheExcludedBound() = runTest {
        val context = ApplicationProvider.getApplicationContext<Context>()
        assertEquals(" ; ", context.getString(R.string.sinnoh_list_separator))
        assertTrue(context.getString(R.string.sinnoh_national).startsWith(" "))
        assertTrue(context.getString(R.string.sinnoh_configuration_details, "", "", "", "").startsWith(" — "))
        val game = FakeGameDao.DIAMOND
        val content = checkNotNull(SinnohRepository(context).content(game))
        val chair = content.underground.goods.single { it.id == 9 }
        val article = sinnohContentArticles(context, game, content).single { it.id == "sinnoh-goods" }
        val paragraph = article.paragraphs.single { it.single().text.startsWith(chair.name) }.single().text
        val expected = context.getString(
            R.string.sinnoh_sphere_price,
            context.getString(R.string.sinnoh_sphere_red),
            8,
            9
        )
        assertTrue(paragraph.contains(expected))
    }

    @Test
    fun factoryIncludesTheFinalOpponentsPoolAndAllTenHallRanks() = runTest {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val game = FakeGameDao.PLATINUM
        val content = checkNotNull(SinnohRepository(context).content(game))
        val articles = sinnohContentArticles(context, game, content)
        assertEquals(46, articles.size)
        assertEquals(10, articles.count { it.id.startsWith("sinnoh-hall-") })
        val firstFactory = articles.single { it.id == "sinnoh-factory-1" }
        val finalPool = context.getString(
            R.string.sinnoh_factory_pool,
            context.getString(R.string.sinnoh_factory_opponent50),
            4
        )
        assertTrue(firstFactory.summary.contains(finalPool))
        assertFalse(
            sinnohContentArticles(
                context,
                FakeGameDao.DIAMOND,
                checkNotNull(SinnohRepository(context).content(FakeGameDao.DIAMOND))
            ).any {
                it.id.startsWith("sinnoh-hall-") || it.id.startsWith("sinnoh-factory-")
            }
        )
    }
}

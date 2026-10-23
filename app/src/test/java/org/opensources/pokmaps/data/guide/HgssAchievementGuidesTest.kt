package org.opensources.pokmaps.data.guide

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class HgssAchievementGuidesTest {
    @Test
    fun bothPreparatoryVersionsReadTheCompleteSharedSetFromCompiledOfflineResources() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val heartgold = achievementGuides(context, 15)
        val soulsilver = achievementGuides(context, 16)
        assertEquals(136, heartgold.size)
        assertEquals(136, heartgold.map { it.achievementId }.toSet().size)
        assertEquals(heartgold.map { it.copy(versions = setOf(16)) }, soulsilver)
        assertTrue(heartgold.all { it.versions == setOf(15) })
        assertTrue(soulsilver.all { it.versions == setOf(16) })
        for (entry in heartgold) {
            assertTrue(context.getString(entry.title).isNotBlank())
            assertTrue(context.getString(entry.text).isNotBlank())
        }
        val challenge = heartgold.single { it.achievementId == 119420 }
        assertEquals(5, challenge.points)
        assertTrue(challenge.missable)
        assertTrue(context.getString(challenge.text).contains("Défini"))
        val national = heartgold.single { it.achievementId == 123898 }
        assertTrue(context.getString(national.text).contains("373"))
        assertTrue(context.getString(national.text).contains("371"))
    }
}

package org.opensources.pokmaps.domain.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.domain.guide.FriendshipRules
import org.opensources.pokmaps.domain.map.MapDestinations
import org.opensources.pokmaps.domain.pokemon.UnownForm

class HgssModelsTest {
    @Test
    fun preparatoryCartridgesKeepTheirOwnIdentityAndCover() {
        listOf(FakeGameDao.HEARTGOLD, FakeGameDao.SOULSILVER).forEach { game ->
            assertEquals(VersionGroup.HEARTGOLD_SOULSILVER, game.versionGroup)
            assertEquals(Generation.GEN4, game.version.generation)
            assertEquals("heartgold-soulsilver", game.mapFamily)
            assertEquals("johto", MapDestinations.startRegion(game.versionGroup))
            assertEquals(2, game.remakeGenerationId)
            assertEquals(28, UnownForm.available(game).size)
            assertThrows(IllegalStateException::class.java) { FriendshipRules.forGame(game) }
        }
        assertEquals(250, FakeGameDao.HEARTGOLD.mascotPokemonId)
        assertEquals(249, FakeGameDao.SOULSILVER.mascotPokemonId)
    }
}

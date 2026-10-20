package org.opensources.pokmaps.data.repository

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.data.db.FakeMapDao
import org.opensources.pokmaps.data.db.MapDao
import org.opensources.pokmaps.data.db.TrainerPokemonRow
import org.opensources.pokmaps.domain.map.RivalChoice
import org.opensources.pokmaps.domain.map.TeamSelection

class Route22RivalRepositoryTest {
    @Test
    fun yellowSharesOneActorAndKeepsFixedAndVariableBattles() = runTest {
        val delegate = FakeMapDao()
        val dao = object : MapDao by delegate {
            override suspend fun maps(versionGroupId: Int, versionId: Int) =
                delegate.maps(versionGroupId, versionId).map {
                    if (it.id == FakeMapDao.ROUTE_1) it.copy(identifier = "route-22") else it
                }

            override suspend fun objects(versionGroupId: Int, versionId: Int) =
                delegate.objects(versionGroupId, versionId).first { it.id == FakeMapDao.TRAINER }.let {
                    listOf(
                        it.copy(sprite = "blue", name = "Rival (1er combat)"),
                        it.copy(id = 999, sprite = "blue", name = "Rival (2e combat)")
                    )
                }

            override suspend fun trainerParty(objectId: Int) = if (objectId == 999) {
                listOf(TrainerPokemonRow(1, "rival-evolution", 135, "Voltali", 1, 135, "Voltali", 53))
            } else {
                listOf(TrainerPokemonRow(1, null, null, null, 1, 133, "Évoli", 8))
            }
        }
        val repository = MapRepository(dao, Dispatchers.Unconfined)
        val yellow = FakeGameDao.RED.copy(
            versionId = 3,
            versionIdentifier = "yellow",
            versionGroupId = 2,
            versionGroupIdentifier = "yellow"
        )
        val actor = repository.catalog(yellow).objects[FakeMapDao.ROUTE_1].orEmpty().single()
        assertEquals("Rival", actor.name)
        val teams = repository.trainerTeams(yellow, actor.id)
        val selection = TeamSelection.of(teams, RivalChoice())
        assertEquals(listOf(null, 1), selection.shown.map { it.rematch })
        assertEquals(listOf(8, 53), selection.shown.map { it.members.single().level })
    }
}

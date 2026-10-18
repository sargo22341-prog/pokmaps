package org.opensources.pokmaps.domain.model

import java.io.File
import java.sql.DriverManager
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.domain.guide.FriendshipRules
import org.opensources.pokmaps.domain.map.MapDestinations
import org.opensources.pokmaps.domain.pokemon.UnownForm

/** Règles propres à chaque jeu, décidées pour les onze versions livrées. */
class VersionGroupMatrixTest {
    private data class Row(
        val group: VersionGroup,
        val mapFamily: String,
        val startRegion: String,
        val friendshipTool: Boolean,
        val unownForms: Int
    )

    private val kanto = Row(VersionGroup.RED_BLUE, "red-blue-yellow", "kanto", false, 0)
    private val johto = Row(VersionGroup.GOLD_SILVER, "gold-silver-crystal", "johto", true, 26)
    private val hoenn = Row(VersionGroup.RUBY_SAPPHIRE, "ruby-sapphire-emerald", "hoenn", true, 0)
    private val remake = Row(VersionGroup.FIRERED_LEAFGREEN, "firered-leafgreen", "kanto", true, 28)
    private val expected = mapOf(
        "red" to kanto,
        "blue" to kanto,
        "yellow" to kanto.copy(group = VersionGroup.YELLOW),
        "gold" to johto,
        "silver" to johto,
        "crystal" to johto.copy(group = VersionGroup.CRYSTAL),
        "ruby" to hoenn,
        "sapphire" to hoenn,
        "emerald" to hoenn.copy(group = VersionGroup.EMERALD),
        "firered" to remake,
        "leafgreen" to remake
    )

    @Test
    fun eachOfTheElevenVersionsHasItsOwnDecidedRules() {
        val actual = FakeGameDao.ELEVEN_GAMES.associate { game ->
            game.versionIdentifier to Row(
                game.versionGroup,
                game.mapFamily,
                MapDestinations.startRegion(game.versionGroup),
                runCatching { FriendshipRules.forGame(game) }.isSuccess,
                UnownForm.available(game).size
            )
        }
        assertEquals(expected, actual)
        assertEquals(
            (VersionGroup.entries.toSet() - setOf(VersionGroup.DIAMOND_PEARL, VersionGroup.PLATINUM)),
            actual.values.map {
                it.group
            }.toSet()
        )
    }

    @Test
    fun theShippedDatabaseHoldsExactlyTheFourteenGamesOfTheTestMatrix() {
        val database = File(System.getProperty("pokemaps.database").orEmpty())
        assertTrue("Asset versionné absent : database/pokedex.db", database.isFile)
        val games = DriverManager.getConnection("jdbc:sqlite:${database.path}").use { connection ->
            connection.createStatement().use { query ->
                query.executeQuery(
                    """
                    SELECT v.id, v.identifier, vg.id AS group_id, vg.identifier AS group_identifier, vg.generation_id
                    FROM version v JOIN version_group vg ON vg.id = v.version_group_id ORDER BY v.id
                    """
                ).use { rows ->
                    buildList {
                        while (rows.next()) {
                            add(
                                listOf(
                                    rows.getInt("id"),
                                    rows.getString("identifier"),
                                    rows.getInt("group_id"),
                                    rows.getString("group_identifier"),
                                    rows.getInt("generation_id")
                                )
                            )
                        }
                    }
                }
            }
        }
        val declared = FakeGameDao.ELEVEN_GAMES + listOf(FakeGameDao.DIAMOND, FakeGameDao.PEARL, FakeGameDao.PLATINUM)
        val matrix = declared.map {
            listOf(it.versionId, it.versionIdentifier, it.versionGroupId, it.versionGroupIdentifier, it.generationId)
        }
        assertEquals(matrix, games)
    }

    @Test
    fun aGroupWithoutRulesIsRejectedInsteadOfBorrowingAnotherGamesRules() {
        val unsupported = FakeGameDao.EMERALD.copy(versionGroupIdentifier = "heartgold-soulsilver")
        assertThrows(IllegalArgumentException::class.java) { unsupported.mapFamily }
    }
}

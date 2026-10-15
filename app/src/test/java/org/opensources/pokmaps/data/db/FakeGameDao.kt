package org.opensources.pokmaps.data.db

import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOf
import org.opensources.pokmaps.domain.model.Game

/** Jeux en mémoire (Or, de la 2e génération, seulement sur demande) ; `failing` simule une base illisible. */
internal class FakeGameDao(private val games: List<Game> = listOf(RED, BLUE), private val failing: Boolean = false) :
    GameDao {
    override fun gameRows(): Flow<List<GameRow>> = error("Le faux fournit directement les jeux du domaine")

    override fun games(): Flow<List<Game>> = if (failing) {
        flow {
            throw IllegalStateException(BROKEN)
        }
    } else {
        flowOf(games)
    }

    companion object {
        val RED = Game(1, "red", "Rouge", 1, "red-blue", 1, CHARIZARD, RED_COLOR)
        val BLUE = Game(2, "blue", "Bleu", 1, "red-blue", 1, BLASTOISE, BLUE_COLOR)
        val GOLD = Game(4, "gold", "Or", 3, "gold-silver", 2, HO_OH, GOLD_COLOR)
        val RUBY = Game(7, "ruby", "Rubis", 5, "ruby-sapphire", 3, 383, 0xA8243A)
        val EMERALD = Game(9, "emerald", "Émeraude", 6, "emerald", 3, 384, 0x2E9A5A)
        val FIRERED = Game(10, "firered", "Rouge Feu", 7, "firered-leafgreen", 3, CHARIZARD, 0xE8642A)
        val GBA_GAMES = listOf(
            RUBY,
            RUBY.copy(versionId = 8, versionIdentifier = "sapphire", name = "Saphir"),
            EMERALD,
            FIRERED,
            FIRERED.copy(versionId = 11, versionIdentifier = "leafgreen", name = "Vert Feuille")
        )

        /** Les onze versions de la base livrée, dans son ordre (identifiants, groupes et générations). */
        val ELEVEN_GAMES = listOf(
            RED,
            BLUE,
            Game(3, "yellow", "Jaune", 2, "yellow", 1, 25, 0xF2C21B),
            GOLD,
            GOLD.copy(versionId = 5, versionIdentifier = "silver", name = "Argent"),
            Game(6, "crystal", "Cristal", 4, "crystal", 2, 245, 0x59BFCB)
        ) + GBA_GAMES
        const val BROKEN = "Base illisible"
        private const val CHARIZARD = 6
        private const val BLASTOISE = 9
        private const val HO_OH = 250
        private const val RED_COLOR = 0xD8302A
        private const val BLUE_COLOR = 0x2A63C4
        private const val GOLD_COLOR = 0xC9A227
    }
}

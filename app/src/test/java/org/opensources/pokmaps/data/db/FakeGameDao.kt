package org.opensources.pokmaps.data.db

import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOf
import org.opensources.pokmaps.domain.model.Game

/** Jeux en mémoire ; `failing` simule une base illisible. */
internal class FakeGameDao(private val games: List<Game> = listOf(RED, BLUE), private val failing: Boolean = false) :
    GameDao {
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
        const val BROKEN = "Base illisible"
        private const val CHARIZARD = 6
        private const val BLASTOISE = 9
        private const val RED_COLOR = 0xD8302A
        private const val BLUE_COLOR = 0x2A63C4
    }
}

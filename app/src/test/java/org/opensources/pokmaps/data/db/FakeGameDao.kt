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
        val DIAMOND = Game(12, "diamond", "Diamant", 8, "diamond-pearl", 4, 483, 0x7D9DC4)
        val PEARL = Game(13, "pearl", "Perle", 8, "diamond-pearl", 4, 484, 0xCF9EB5)
        val PLATINUM = Game(14, "platinum", "Platine", 9, "platinum", 4, 487, 0xA49A72)
        val HEARTGOLD = Game(
            15, "heartgold", "Or HeartGold", 10, "heartgold-soulsilver", 4, 250, 0xC9A227,
            remakeGenerationId = 2, hasTimeOfDay = true
        )
        val SOULSILVER = HEARTGOLD.copy(
            versionId = 16,
            versionIdentifier = "soulsilver",
            name = "Argent SoulSilver",
            mascotPokemonId = 249,
            color = 0x9DA9B5
        )
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

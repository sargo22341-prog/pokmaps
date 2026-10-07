package org.opensources.pokmaps.data.db

/** Attaques en mémoire : Tonnerre (CT24) et Rugissement, sans CT ; `failing` simule une base illisible. */
internal class FakeMoveDao(private val failing: Boolean = false) : MoveDao {
    override suspend fun move(moveId: Int, versionGroupId: Int) = read {
        when (moveId) {
            THUNDERBOLT -> MoveRow(
                THUNDERBOLT, "Tonnerre", 95, 100, 15, "special", PARALYSIS, CHANCE, 13, "electric", "Électrik",
                "tm24", "CT24"
            )

            GROWL -> MoveRow(
                GROWL, "Rugissement", null, 100, 40, "status", LOWER_ATTACK, null, 1, "normal", "Normal", null, null
            )

            else -> null
        }
    }

    private fun <T> read(rows: () -> T): T = if (failing) throw IllegalStateException(FakeGameDao.BROKEN) else rows()

    companion object {
        const val THUNDERBOLT = 85
        const val GROWL = 45
        const val PARALYSIS = "Inflige des dégâts et peut paralyser la cible."
        const val CHANCE = 10.15625
        private const val LOWER_ATTACK = "Baisse l’Attaque de la cible d’un niveau."
    }
}

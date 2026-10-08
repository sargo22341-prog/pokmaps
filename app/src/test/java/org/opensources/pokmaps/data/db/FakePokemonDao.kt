package org.opensources.pokmaps.data.db

/**
 * Fiche de Pikachu en mémoire (seul Pokémon connu) ; `failing` simule une base illisible. Il tient un Ballon Lumière
 * dans Bleu seulement, pour vérifier que les objets tenus sont ceux de la version choisie.
 */
internal class FakePokemonDao(private val failing: Boolean = false) : PokemonDao {
    override suspend fun breedingProfiles(versionGroupId: Int): List<BreedingRow> = emptyList()

    override suspend fun pokemon(pokemonId: Int) = read {
        if (pokemonId == PIKACHU) {
            PokemonRow(PIKACHU, "Pikachu", "Pikachu", "Souris", null, 4, 60, 190, "Moyenne", 10, HALF_FEMALE, 10)
        } else {
            null
        }
    }

    override suspend fun number(pokemonId: Int, versionGroupId: Int) = read { PIKACHU }

    override suspend fun types(pokemonId: Int, generationId: Int) = read { listOf(TypeRow(13, "electric", "Électrik")) }

    override suspend fun stats(pokemonId: Int, generationId: Int) =
        read { listOf(StatRow("hp", "PV", 35), StatRow("speed", "Vitesse", 90)) }

    override suspend fun typeFactors(generationId: Int) = read { emptyList<TypeFactorRow>() }

    override suspend fun chainMembers(chainId: Int) =
        read { listOf(ChainMemberRow(PIKACHU, "Pikachu"), ChainMemberRow(26, "Raichu")) }

    override suspend fun evolutions(chainId: Int, versionGroupId: Int) =
        read { listOf(EvolutionRow(PIKACHU, 26, "use-item", null, "Pierre Foudre", "thunder-stone", true)) }

    override suspend fun moves(pokemonId: Int, versionGroupId: Int) = read {
        listOf(
            electricMove(LEVEL_UP, 1, THUNDER_SHOCK, "Éclair", power = 40, pp = 30, machine = null),
            electricMove(MACHINE, 0, THUNDERBOLT, "Tonnerre", power = 95, pp = 15, machine = "CT24" to "tm24"),
            *if (versionGroupId == FakeGameDao.GOLD.versionGroupId) {
                arrayOf(
                    electricMove("egg", 0, 117, "Patience", power = null, pp = 10, machine = null),
                    electricMove("tutor", 0, 87, "Fatal-Foudre", power = 120, pp = 10, machine = null)
                )
            } else {
                emptyArray()
            }
        )
    }

    override suspend fun encounters(pokemonId: Int) = read { emptyList<EncounterRow>() }

    override suspend fun staticCount(pokemonId: Int, versionGroupId: Int) = read { 0 }

    override suspend fun heldItems(pokemonId: Int, versionId: Int) = read {
        if (versionId == FakeGameDao.BLUE.versionId) {
            listOf(HeldItemRow("light-ball", "Ballon Lumière", hasSprite = true, rarity = 5))
        } else {
            emptyList()
        }
    }

    override suspend fun eggGroups(pokemonId: Int) = read { listOf("Terrestre", "Féerique") }

    override suspend fun abilities(pokemonId: Int, generationId: Int, versionGroupId: Int) =
        read { listOf(AbilityRow("Statik", "Peut paralyser au contact.", false)) }

    private fun electricMove(
        method: String,
        level: Int,
        moveId: Int,
        name: String,
        power: Int?,
        pp: Int,
        machine: Pair<String, String>?
    ) = LearnedMoveRow(
        method, level, moveId, name, power, 100, pp, SPECIAL, 13, "electric", "Électrik",
        machine = machine?.first,
        machineIdentifier = machine?.second
    )

    private fun <T> read(rows: () -> T): T = if (failing) throw IllegalStateException(FakeGameDao.BROKEN) else rows()

    companion object {
        const val PIKACHU = 25
        const val THUNDER_SHOCK = 84
        const val THUNDERBOLT = 85
        private const val HALF_FEMALE = 4
        private const val LEVEL_UP = "level-up"
        private const val MACHINE = "machine"
        private const val SPECIAL = "special"
    }
}

package org.opensources.pokmaps.data.db

/** Fiche de Pikachu en mémoire (seul Pokémon connu) ; `failing` simule une base illisible. */
internal class FakePokemonDao(private val failing: Boolean = false) : PokemonDao {
    override suspend fun pokemon(pokemonId: Int) = read {
        if (pokemonId == PIKACHU) {
            PokemonRow(PIKACHU, "Pikachu", "Pikachu", "Souris", null, 4, 60, 190, "Moyenne", 10)
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

    override suspend fun moves(pokemonId: Int, versionGroupId: Int) = read { emptyList<LearnedMoveRow>() }

    override suspend fun encounters(pokemonId: Int) = read { emptyList<EncounterRow>() }

    override suspend fun staticCount(pokemonId: Int, versionGroupId: Int) = read { 0 }

    private fun <T> read(rows: () -> T): T = if (failing) throw IllegalStateException(FakeGameDao.BROKEN) else rows()

    companion object {
        const val PIKACHU = 25
    }
}

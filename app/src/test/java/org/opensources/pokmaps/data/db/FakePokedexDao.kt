package org.opensources.pokmaps.data.db

/** Petit Pokédex en mémoire (Abo, Arbok, Sabelette, Évoli, Aquali) ; `failing` simule une base illisible. */
internal class FakePokedexDao(private val failing: Boolean = false) : PokedexDao {
    override suspend fun pokedex(versionGroupId: Int) = read {
        listOf(
            PokedexRow(23, 23, "Abo", "Ekans"),
            PokedexRow(24, 24, "Arbok", "Arbok"),
            PokedexRow(27, 27, "Sabelette", "Sandshrew"),
            PokedexRow(133, 133, "Évoli", "Eevee"),
            PokedexRow(134, 134, "Aquali", "Vaporeon")
        )
    }

    override suspend fun pokemonTypes(generationId: Int) = read {
        listOf(
            PokemonTypeRow(23, 1, POISON, "poison", "Poison"),
            PokemonTypeRow(24, 1, POISON, "poison", "Poison"),
            PokemonTypeRow(27, 1, 5, "ground", "Sol"),
            PokemonTypeRow(133, 1, 1, "normal", "Normal"),
            PokemonTypeRow(134, 1, 11, "water", "Eau")
        )
    }

    override suspend fun types(generationId: Int) = read {
        listOf(
            TypeRow(1, "normal", "Normal"),
            TypeRow(POISON, "poison", "Poison"),
            TypeRow(5, "ground", "Sol"),
            TypeRow(11, "water", "Eau")
        )
    }

    override suspend fun encounterMethods(versionId: Int) = read {
        when (versionId) {
            1 -> listOf(PokemonMethodRow(23, "walk"), PokemonMethodRow(133, "gift"))
            else -> listOf(PokemonMethodRow(27, "walk"), PokemonMethodRow(133, "gift"))
        }
    }

    override suspend fun staticPokemon(versionGroupId: Int) = read { emptyList<PokemonMethodRow>() }

    override suspend fun evolutions(versionGroupId: Int) =
        read { listOf(EvolutionPairRow(23, 24), EvolutionPairRow(133, 134)) }

    private fun <T> read(rows: () -> T): T = if (failing) throw IllegalStateException(FakeGameDao.BROKEN) else rows()

    companion object {
        const val POISON = 4
    }
}

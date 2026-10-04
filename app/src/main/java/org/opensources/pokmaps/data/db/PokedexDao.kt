package org.opensources.pokmaps.data.db

import androidx.room.Dao
import androidx.room.Query
import kotlinx.coroutines.flow.Flow
import org.opensources.pokmaps.domain.model.PokedexEntry

@Dao
interface PokedexDao {
    /** Pokédex régional du groupe de versions (Kanto pour Rouge/Bleu/Jaune). */
    @Query(
        """
        SELECT min(pe.number) AS number, p.id AS pokemonId, p.name_fr AS name
        FROM pokedex_entry pe
        JOIN version_group_pokedex vgp ON vgp.pokedex_id = pe.pokedex_id
        JOIN pokemon p ON p.id = pe.pokemon_id
        WHERE vgp.version_group_id = :versionGroupId
        GROUP BY p.id
        ORDER BY number
        """
    )
    fun pokedex(versionGroupId: Int): Flow<List<PokedexEntry>>
}

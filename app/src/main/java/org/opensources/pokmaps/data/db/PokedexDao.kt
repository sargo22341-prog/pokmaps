package org.opensources.pokmaps.data.db

import androidx.room.Dao
import androidx.room.Query

@Dao
interface PokedexDao {
    /** Pokédex régional du groupe de versions (Kanto pour Rouge/Bleu/Jaune). */
    @Query(
        """
        SELECT min(pe.number) AS number, p.id AS pokemonId, p.name_fr AS name, p.name_en AS nameEn
        FROM pokedex_entry pe
        JOIN version_group_pokedex vgp ON vgp.pokedex_id = pe.pokedex_id
        JOIN pokemon p ON p.id = pe.pokemon_id
        WHERE vgp.version_group_id = :versionGroupId
        GROUP BY p.id
        ORDER BY number
        """
    )
    suspend fun pokedex(versionGroupId: Int): List<PokedexRow>

    /** Types de chaque Pokémon dans une génération (types d'origine, ex. Magnéti sans le type Acier). */
    @Query(
        """
        SELECT pt.pokemon_id AS pokemonId, pt.slot AS slot, t.id AS id, t.identifier AS identifier, t.name_fr AS name
        FROM pokemon_type pt JOIN type t ON t.id = pt.type_id
        WHERE pt.generation_id = :generationId
        ORDER BY pt.pokemon_id, pt.slot
        """
    )
    suspend fun pokemonTypes(generationId: Int): List<PokemonTypeRow>

    /** Types existant dans une génération. */
    @Query("SELECT id, identifier, name_fr AS name FROM type WHERE generation_id <= :generationId ORDER BY id")
    suspend fun types(generationId: Int): List<TypeRow>

    /** Méthodes de rencontre de chaque Pokémon dans une version. */
    @Query(
        """
        SELECT DISTINCT e.pokemon_id AS pokemonId, m.identifier AS method
        FROM encounter e JOIN encounter_method m ON m.id = e.method_id
        WHERE e.version_id = :versionId
        """
    )
    suspend fun encounterMethods(versionId: Int): List<PokemonMethodRow>

    /** Pokémon fixes placés sur les cartes du jeu (au cas où ils manqueraient dans les rencontres). */
    @Query(
        """
        SELECT DISTINCT o.pokemon_id AS pokemonId, 'static' AS method
        FROM map_object o JOIN map m ON m.id = o.map_id
        WHERE m.version_group_id = :versionGroupId AND o.kind = 'pokemon' AND o.pokemon_id IS NOT NULL
        """
    )
    suspend fun staticPokemon(versionGroupId: Int): List<PokemonMethodRow>

    @Query(
        "SELECT from_pokemon_id AS fromId, to_pokemon_id AS toId FROM evolution WHERE version_group_id = :versionGroupId"
    )
    suspend fun evolutions(versionGroupId: Int): List<EvolutionPairRow>
}

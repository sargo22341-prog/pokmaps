package org.opensources.pokmaps.data.db

import androidx.room.ColumnInfo
import androidx.room.Entity
import org.opensources.pokmaps.domain.pokemon.PokemonForm

@Entity(tableName = "pokemon_form", primaryKeys = ["version_id", "pokemon_id", "identifier"])
data class PokemonFormEntity(
    @ColumnInfo(name = "version_id") val versionId: Int,
    @ColumnInfo(name = "pokemon_id") val pokemonId: Int,
    val identifier: String,
    @ColumnInfo(name = "name_fr") val name: String,
    @ColumnInfo(name = "sprite_folder") val folder: String,
    @ColumnInfo(name = "sprite_identifier") val spriteIdentifier: String,
    @ColumnInfo(name = "is_default") val isDefault: Boolean,
    @ColumnInfo(name = "sort_order") val sortOrder: Int,
    val hp: Int,
    val attack: Int,
    val defense: Int,
    @ColumnInfo(name = "special_attack") val specialAttack: Int,
    @ColumnInfo(name = "special_defense") val specialDefense: Int,
    val speed: Int
) {
    fun toForm() = PokemonForm(
        pokemonId,
        identifier,
        name,
        folder,
        spriteIdentifier,
        isDefault,
        mapOf(
            "hp" to hp,
            "attack" to attack,
            "defense" to defense,
            "special-attack" to specialAttack,
            "special-defense" to specialDefense,
            "speed" to speed
        )
    )
}

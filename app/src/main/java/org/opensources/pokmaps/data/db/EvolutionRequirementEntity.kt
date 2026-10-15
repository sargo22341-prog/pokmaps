package org.opensources.pokmaps.data.db

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

/** Conditions DS conservées dans la base avant l'activation des jeux dans l'interface. */
@Entity(tableName = "evolution_requirement")
data class EvolutionRequirementEntity(
    @PrimaryKey @ColumnInfo(name = "evolution_id") val evolutionId: Int,
    @ColumnInfo(name = "location_id") val locationId: Int?,
    @ColumnInfo(name = "gender_id") val genderId: Int?,
    @ColumnInfo(name = "party_species_id") val partySpeciesId: Int?,
    @ColumnInfo(name = "near_special_rock") val nearSpecialRock: Int?,
    @ColumnInfo(name = "required_form_id") val requiredFormId: Int?,
    @ColumnInfo(name = "evolved_form_id") val evolvedFormId: Int?
)

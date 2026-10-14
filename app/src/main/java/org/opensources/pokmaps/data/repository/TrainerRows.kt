package org.opensources.pokmaps.data.repository

import org.opensources.pokmaps.data.db.TrainerMoveRow
import org.opensources.pokmaps.data.db.TrainerPokemonRow
import org.opensources.pokmaps.domain.map.TeamVariant
import org.opensources.pokmaps.domain.map.TeamVariantKind
import org.opensources.pokmaps.domain.model.PokemonType
import org.opensources.pokmaps.domain.pokemon.DamageClass
import org.opensources.pokmaps.domain.pokemon.LearnedMove

/** Variante qui nomme l'équipe de ce Pokémon, nulle pour un dresseur à équipe unique. */
internal fun TrainerPokemonRow.toVariant(): TeamVariant? = variantKind?.let { kind ->
    TeamVariant(
        kind = TeamVariantKind.from(kind),
        pokemonId = requireNotNull(variantPokemonId) { "Variante d'équipe sans Pokémon : $this" },
        pokemonName = requireNotNull(variantName) { "Variante d'équipe sans nom : $this" }
    )
}

internal fun TrainerMoveRow.toLearnedMove() = LearnedMove(
    moveId = moveId,
    name = name,
    type = PokemonType(typeId, typeIdentifier, typeName),
    damageClass = DamageClass.from(damageClass),
    power = power,
    accuracy = accuracy,
    pp = pp
)

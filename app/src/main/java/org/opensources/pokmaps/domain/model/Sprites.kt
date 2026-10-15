package org.opensources.pokmaps.domain.model

import org.opensources.pokmaps.domain.pokemon.PokemonForm

/** Chemins des images dans les assets, en WebP sans perte (générées par tools/build_data.py). */
object Sprites {
    /**
     * Sprite d'un Pokémon (Noir et Blanc, PokeAPI/sprites), le même partout : animé, ou sa première image fixe,
     * de même taille ; en couleurs normales ou chromatiques (`shiny`).
     */
    fun pokemon(
        pokemonId: Int,
        animated: Boolean,
        shiny: Boolean = false,
        forms: Map<Int, List<PokemonForm>> = emptyMap()
    ): String {
        forms[pokemonId]?.single { it.isDefault }?.let { return it.sprite(animated, shiny) }
        val style = if (shiny) "sprites/pokemon/shiny" else "sprites/pokemon"
        return if (animated) "$style/animated/$pokemonId.webp" else "$style/static/$pokemonId.webp"
    }

    /** Icône d'un objet (pokesprite), ex. « fire-stone ». */
    fun item(identifier: String) = "sprites/items/$identifier.webp"

    /** Sprite d'un PNJ ou d'un objet sur la carte (pret), ex. « youngster ». */
    fun mapSprite(versionGroupIdentifier: String, sprite: String) = "maps/$versionGroupIdentifier/sprites/$sprite.webp"

    /** Uri d'un fichier des assets, lisible par Coil. */
    fun assetUri(path: String) = "file:///android_asset/$path"
}

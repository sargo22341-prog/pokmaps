package org.opensources.pokmaps.domain.model

/** Chemins des images dans les assets, en WebP sans perte (générées par tools/build_data.py). */
object Sprites {
    /**
     * Sprite d'un Pokémon (Noir et Blanc, PokeAPI/sprites), le même partout : animé, ou sa première image fixe,
     * de même taille.
     */
    fun pokemon(pokemonId: Int, animated: Boolean) =
        if (animated) "sprites/pokemon/animated/$pokemonId.webp" else "sprites/pokemon/static/$pokemonId.webp"

    /** Icône d'un objet (pokesprite), ex. « fire-stone ». */
    fun item(identifier: String) = "sprites/items/$identifier.webp"

    /** Sprite d'un PNJ ou d'un objet sur la carte (pret), ex. « youngster ». */
    fun mapSprite(versionGroupIdentifier: String, sprite: String) = "maps/$versionGroupIdentifier/sprites/$sprite.webp"

    /** Uri d'un fichier des assets, lisible par Coil. */
    fun assetUri(path: String) = "file:///android_asset/$path"
}

package org.opensources.pokmaps.domain.model

/** Chemins des images dans les assets (générées par tools/build_data.py). */
object Sprites {
    /** Icône de boîte (pokesprite). */
    fun pokemonIcon(pokemonId: Int) = "sprites/pokemon/icon/$pokemonId.png"

    /** Sprite du Pokémon dans le jeu (PokeAPI/sprites). */
    fun pokemonSprite(versionGroupIdentifier: String, pokemonId: Int) =
        "sprites/pokemon/$versionGroupIdentifier/$pokemonId.png"

    /** Icône d'un objet (pokesprite), ex. « fire-stone ». */
    fun item(identifier: String) = "sprites/items/$identifier.png"

    /** Sprite d'un PNJ ou d'un objet sur la carte (pret), ex. « youngster ». */
    fun mapSprite(versionGroupIdentifier: String, sprite: String) = "maps/$versionGroupIdentifier/sprites/$sprite.png"

    /** Artwork officiel, chargé en ligne depuis PokeAPI/sprites (commit figé, comme les sprites embarqués). */
    fun officialArtwork(pokemonId: Int) =
        "https://raw.githubusercontent.com/PokeAPI/sprites/$POKEAPI_SPRITES_COMMIT/sprites/pokemon/other/official-artwork/$pokemonId.png"

    /** Uri d'un fichier des assets, lisible par Coil. */
    fun assetUri(path: String) = "file:///android_asset/$path"

    // Même commit que tools/pokemaps_data/sources.py.
    private const val POKEAPI_SPRITES_COMMIT = "bfb75391935310368065096fa08c51e8970bc43e"
}

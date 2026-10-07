package org.opensources.pokmaps.domain.model

/**
 * Endroits de l'application où un Pokémon est dessiné : chacun peut avoir des sprites animés ou fixes (réglages).
 * Le sprite fixe est la première image du sprite animé, à la même taille.
 */
enum class SpritePlace(val identifier: String) {
    /** Pokémon sauvages et fixes dessinés sur la carte. */
    MAP("map"),

    /** Liste des Pokémon du lieu et fiche de l'élément touché, sur la carte. */
    MAP_LIST("map_list"),

    POKEDEX("pokedex"),

    /** Grande image de la fiche d'un Pokémon. */
    POKEMON_SHEET("pokemon_sheet"),

    /** Lignes d'évolution (fiche Pokémon, pierres et fossiles). */
    EVOLUTIONS("evolutions"),

    /** Fiches des lieux, des personnages et des objets. */
    SHEETS("sheets"),

    SEARCH("search");

    companion object {
        /** Animés par défaut : le Pokédex et la fiche Pokémon, comme avant le réglage par endroit. */
        val DEFAULT_ANIMATED: Set<SpritePlace> = setOf(POKEDEX, POKEMON_SHEET)

        /** Endroit d'après son identifiant mémorisé, null s'il est inconnu (réglage d'une autre version). */
        fun fromIdentifier(identifier: String): SpritePlace? = entries.firstOrNull { it.identifier == identifier }
    }
}

package org.opensources.pokmaps.domain.model

/**
 * Jeu choisi par l'utilisateur. Il fixe la version (rencontres), le groupe de versions
 * (attaques, cartes, sprites) et la génération (types, stats, table des types) utilisés dans toute l'application.
 * `mascotPokemonId` et `color` (0xRRGGBB) dessinent sa jaquette.
 */
data class Game(
    val versionId: Int,
    val versionIdentifier: String,
    val name: String,
    val versionGroupId: Int,
    val versionGroupIdentifier: String,
    val generationId: Int,
    val mascotPokemonId: Int,
    val color: Int,
    val remakeGenerationId: Int? = null,
    val hasTimeOfDay: Boolean = false
) {
    /** Groupe de versions, dont la prise en charge est vérifiée à la lecture des jeux (GameRepository). */
    val versionGroup: VersionGroup get() = VersionGroup.of(versionGroupIdentifier)

    /** Familles de plans communes, également utilisées par le pipeline pour les emplacements relus. */
    val mapFamily: String get() = versionGroup.mapFamily
}

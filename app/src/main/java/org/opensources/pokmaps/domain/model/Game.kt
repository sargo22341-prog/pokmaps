package org.opensources.pokmaps.domain.model

/**
 * Jeu choisi par l'utilisateur (Rouge, Bleu ou Jaune). Il fixe la version (rencontres), le groupe de versions
 * (attaques, cartes, sprites) et la génération (types, stats, table des types) utilisés dans toute l'application.
 */
data class Game(
    val versionId: Int,
    val versionIdentifier: String,
    val name: String,
    val versionGroupId: Int,
    val versionGroupIdentifier: String,
    val generationId: Int
)

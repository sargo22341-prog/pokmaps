package org.opensources.pokmaps.domain.model

/**
 * Groupes de versions dont l'application connaît les règles. Une règle propre à un jeu s'écrit dans son thème par un
 * `when` exhaustif sur ce type : un groupe ajouté signale à la compilation chaque règle à décider, au lieu d'hériter
 * de celle d'un autre jeu. Un groupe de la base absent d'ici est refusé à la lecture des jeux (GameRepository).
 *
 * `mapFamily` : plans communs, sous les mêmes noms que `map_family` dans tools/pokemaps_data/games.py.
 */
enum class VersionGroup(val identifier: String, val mapFamily: String) {
    RED_BLUE("red-blue", "red-blue-yellow"),
    YELLOW("yellow", "red-blue-yellow"),
    GOLD_SILVER("gold-silver", "gold-silver-crystal"),
    CRYSTAL("crystal", "gold-silver-crystal"),
    RUBY_SAPPHIRE("ruby-sapphire", "ruby-sapphire-emerald"),
    EMERALD("emerald", "ruby-sapphire-emerald"),
    FIRERED_LEAFGREEN("firered-leafgreen", "firered-leafgreen");

    companion object {
        fun of(identifier: String): VersionGroup = requireNotNull(entries.firstOrNull { it.identifier == identifier }) {
            "Groupe de versions sans règles dans l'application : $identifier"
        }

        fun isSupported(identifier: String): Boolean = entries.any { it.identifier == identifier }
    }
}

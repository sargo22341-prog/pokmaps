package org.opensources.pokmaps.domain.pokemon

/** Alphabet complet ; les signes de ponctuation apparaissent à partir de la troisième génération. */
enum class UnownForm(val identifier: String, val symbol: String, val firstGeneration: Int = 2) {
    A("a", "A"),
    B("b", "B"),
    C("c", "C"),
    D("d", "D"),
    E("e", "E"),
    F("f", "F"),
    G("g", "G"),
    H("h", "H"),
    I("i", "I"),
    J("j", "J"),
    K("k", "K"),
    L("l", "L"),
    M("m", "M"),
    N("n", "N"),
    O("o", "O"),
    P("p", "P"),
    Q("q", "Q"),
    R("r", "R"),
    S("s", "S"),
    T("t", "T"),
    U("u", "U"),
    V("v", "V"),
    W("w", "W"),
    X("x", "X"),
    Y("y", "Y"),
    Z("z", "Z"),
    EXCLAMATION("exclamation", "!", 3),
    QUESTION("question", "?", 3);

    fun sprite(animated: Boolean, shiny: Boolean): String {
        val style = if (shiny) "shiny/" else ""
        val motion = if (animated) "animated" else "static"
        return "sprites/unown/$style$motion/$identifier.webp"
    }

    companion object {
        const val POKEMON_ID = 201

        fun available(generation: Int): List<UnownForm> = entries.filter { it.firstGeneration <= generation }

        fun from(identifier: String): UnownForm = requireNotNull(entries.firstOrNull { it.identifier == identifier }) {
            "Forme de Zarbi inconnue : $identifier"
        }
    }
}

package org.opensources.pokmaps.data.json

/** Borne la profondeur avant le parseur Android, pour qu'un fichier externe ne sature pas sa pile. */
internal object JsonLimits {
    fun validate(text: String, maxCharacters: Int) {
        require(text.length <= maxCharacters)
        var depth = 0
        var quoted = false
        var escaped = false
        for (character in text) {
            if (quoted) {
                when {
                    escaped -> escaped = false
                    character == '\\' -> escaped = true
                    character == '"' -> quoted = false
                }
                continue
            }
            when (character) {
                '"' -> quoted = true

                '{', '[' -> {
                    depth += 1
                    require(depth <= MAX_DEPTH)
                }

                '}', ']' -> {
                    depth -= 1
                    require(depth >= 0)
                }
            }
        }
        require(!quoted && depth == 0)
    }

    private const val MAX_DEPTH = 16
}

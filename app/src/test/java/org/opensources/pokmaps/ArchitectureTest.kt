package org.opensources.pokmaps

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Règles d'AGENTS.md vérifiables sur les sources : taille des fichiers et sens des dépendances. */
class ArchitectureTest {
    // Les tests JVM s'exécutent depuis le dossier du module app.
    private val repository = File("..").canonicalFile
    private val main = File("src/main/java/org/opensources/pokmaps")

    private fun sources(root: File, extension: String): List<File> = root.walkTopDown()
        .onEnter { it.name !in IGNORED_DIRECTORIES }
        .filter { it.isFile && it.extension == extension }
        .toList()

    private fun File.imports(): List<String> =
        readLines().filter { it.startsWith("import ") }.map { it.removePrefix("import ").trim() }

    private fun File.relative(): String = relativeTo(repository).invariantSeparatorsPath

    @Test
    fun sourceFilesStayUnder600Lines() {
        val files = sources(File("src"), "kt") + sources(File(repository, "tools"), "py")
        assertTrue("aucune source trouvée depuis ${File(".").canonicalPath}", files.size > 100)
        val tooLong = files.filter { it.readLines().size > MAX_FILE_LINES }.map { it.relative() }
        assertEquals(emptyList<String>(), tooLong)
    }

    @Test
    fun uiNeverImportsData() {
        val offenders = sources(File(main, "ui"), "kt")
            .filter { file -> file.imports().any { it.startsWith("$PACKAGE.data.") } }
            .map { it.relative() }
        assertEquals(emptyList<String>(), offenders)
    }

    @Test
    fun pureDomainHasNoAndroidNorData() {
        val offenders = PURE_DOMAIN.flatMap { sources(File(main, "domain/$it"), "kt") }.filter { file ->
            file.imports().any { import ->
                import.startsWith("android.") || import.startsWith("androidx.") || import.startsWith("$PACKAGE.data.")
            }
        }.map { it.relative() }
        assertEquals(emptyList<String>(), offenders)
    }

    @Test
    fun claudeInstructionsOnlyImportAgents() {
        val lines = File(repository, ".claude/CLAUDE.md").readLines()
        assertTrue(lines.any { it.trim() == "@../AGENTS.md" })
        // Une règle recopiée (liste, tableau, titre de section) finirait par diverger d'AGENTS.md.
        val rules = lines.filter { RULE_LINE.containsMatchIn(it) }
        assertEquals(emptyList<String>(), rules)
    }

    private companion object {
        const val PACKAGE = "org.opensources.pokmaps"
        const val MAX_FILE_LINES = 600
        val PURE_DOMAIN = listOf("model", "map", "pokemon", "pokedex", "guide")
        val IGNORED_DIRECTORIES = setOf("build", ".venv", ".cache", "__pycache__", ".ruff_cache", ".pytest_cache")
        val RULE_LINE = Regex("""^\s*([-*+|]|\d+\.|##)""")
    }
}

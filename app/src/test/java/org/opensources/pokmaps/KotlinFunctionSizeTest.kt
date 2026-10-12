package org.opensources.pokmaps

import java.io.File
import org.jetbrains.kotlin.CoreEnvironmentDeprecation
import org.jetbrains.kotlin.cli.extensionsStorage
import org.jetbrains.kotlin.cli.jvm.compiler.EnvironmentConfigFiles
import org.jetbrains.kotlin.cli.jvm.compiler.KotlinCoreEnvironment
import org.jetbrains.kotlin.com.intellij.openapi.util.Disposer
import org.jetbrains.kotlin.com.intellij.psi.PsiErrorElement
import org.jetbrains.kotlin.com.intellij.psi.util.PsiTreeUtil
import org.jetbrains.kotlin.compiler.plugin.CompilerPluginRegistrar
import org.jetbrains.kotlin.compiler.plugin.ExperimentalCompilerApi
import org.jetbrains.kotlin.config.CompilerConfiguration
import org.jetbrains.kotlin.psi.KtNamedFunction
import org.jetbrains.kotlin.psi.KtPsiFactory
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Le compilateur reconnaît les fonctions locales et les corps expression, même au milieu des chaînes. */
class KotlinFunctionSizeTest {
    @Test
    fun kotlinFunctionsStayUnder60Lines() = withParser { factory ->
        val root = File("src")
        val files = root.walkTopDown().filter { it.isFile && it.extension == "kt" }.toList()
        assertTrue("aucune source Kotlin trouvée", files.size > 100)
        val offenders = files.flatMap { file ->
            oversizedFunctions(factory, file.readText(), file.invariantSeparatorsPath)
                .map { "${file.invariantSeparatorsPath}:$it" }
        }
        assertEquals(emptyList<String>(), offenders)
    }

    @Test
    fun countsExpressionAndLocalFunctionsWithBothLineEndings() = withParser { factory ->
        val source = "fun outer() {\nfun local() = listOf(\n" + "1,\n".repeat(59) + ")\n}\n"
        val expected = listOf("outer (63 lignes)", "local (61 lignes)")
        assertEquals(expected, oversizedFunctions(factory, source))
        assertEquals(expected, oversizedFunctions(factory, source.replace("\n", "\r\n")))
        assertEquals(expected, oversizedFunctions(factory, "\uFEFF$source"))
        val valid = "fun valid() = listOf(\n" + "1,\n".repeat(58) + ")"
        assertEquals(emptyList<String>(), oversizedFunctions(factory, valid))
    }

    @Test
    fun ignoresBracesAndFakeFunctionsInsideStringsAndComments() = withParser { factory ->
        val source = "fun valid() = \"fun fake() {\"\n/* fun comment() { */"
        assertEquals(emptyList<String>(), oversizedFunctions(factory, source))
    }

    private fun oversizedFunctions(factory: KtPsiFactory, source: String, path: String = "fixture.kt"): List<String> {
        val normalized = source.removePrefix("\uFEFF").replace("\r\n", "\n")
        val parsed = factory.createFile(normalized)
        val errors = PsiTreeUtil.findChildrenOfType(parsed, PsiErrorElement::class.java)
        assertTrue("$path : source Kotlin invalide : ${errors.map { it.errorDescription }}", errors.isEmpty())
        return PsiTreeUtil.findChildrenOfType(parsed, KtNamedFunction::class.java).mapNotNull { function ->
            val lines = normalized.substring(function.textRange.startOffset, function.textRange.endOffset)
                .count { it == '\n' } + 1
            if (lines > 60) "${function.name} ($lines lignes)" else null
        }
    }

    // API isolée au test de syntaxe, avec la même version épinglée que le compilateur du projet.
    @OptIn(CoreEnvironmentDeprecation::class, CompilerConfiguration.Internals::class, ExperimentalCompilerApi::class)
    private fun withParser(check: (KtPsiFactory) -> Unit) {
        val disposable = Disposer.newDisposable()
        try {
            val environment = KotlinCoreEnvironment.createForProduction(
                disposable,
                CompilerConfiguration().apply { extensionsStorage = CompilerPluginRegistrar.ExtensionStorage() },
                EnvironmentConfigFiles.JVM_CONFIG_FILES
            )
            check(KtPsiFactory(environment.project, false))
        } finally {
            Disposer.dispose(disposable)
        }
    }
}

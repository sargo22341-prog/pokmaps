import com.github.benmanes.gradle.versions.updates.DependencyUpdatesTask

plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.compose) apply false
    alias(libs.plugins.ksp) apply false
    alias(libs.plugins.hilt) apply false
    alias(libs.plugins.gradle.versions)
}

private fun String.isNonStableVersion(): Boolean {
    val stableKeyword = listOf("RELEASE", "FINAL", "GA").any { uppercase().contains(it) }
    val stablePattern = "^[0-9,.v-]+(-r)?$".toRegex()
    return !stableKeyword && !stablePattern.matches(this)
}

tasks.named<DependencyUpdatesTask>("dependencyUpdates") {
    revision = "release"
    gradleReleaseChannel = "current"
    notCompatibleWithConfigurationCache(
        "dependencyUpdates consulte les dépôts à chaque exécution."
    )
    rejectVersionIf { candidate.version.isNonStableVersion() }
}

// ktlint est lancé directement via sa CLI : pas de plugin Gradle tiers à maintenir.
val ktlint = configurations.create("ktlint")

dependencies {
    ktlint(libs.ktlint.cli) {
        attributes {
            attribute(Bundling.BUNDLING_ATTRIBUTE, objects.named(Bundling.EXTERNAL))
        }
    }
}

val ktlintPatterns = listOf("**/src/**/*.kt", "**/*.gradle.kts", "!**/build/**")

tasks.register<JavaExec>("ktlintCheck") {
    group = "verification"
    description = "Vérifie le style du code Kotlin avec ktlint."
    classpath = ktlint
    mainClass.set("com.pinterest.ktlint.Main")
    args = listOf("--relative") + ktlintPatterns
}

tasks.register<JavaExec>("ktlintFormat") {
    group = "formatting"
    description = "Corrige automatiquement le style du code Kotlin avec ktlint."
    classpath = ktlint
    mainClass.set("com.pinterest.ktlint.Main")
    args = listOf("-F", "--relative") + ktlintPatterns
}

import org.gradle.api.artifacts.component.ModuleComponentIdentifier

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.ksp)
    alias(libs.plugins.hilt)
}

// Version injectée par la CI à partir du tag git (ex. v1.2.3 -> 1.2.3 / 10203).
val appVersionName = providers.gradleProperty("versionName").getOrElse("0.1.0-dev")
val appVersionCode = providers.gradleProperty("versionCode").map(String::toInt).getOrElse(1)

// Signature de la release : fournie par la CI via des variables d'environnement.
val releaseKeystore = providers.environmentVariable("POKEMAPS_KEYSTORE_FILE")

android {
    namespace = "org.opensources.pokmaps"
    compileSdk = 37

    defaultConfig {
        applicationId = "org.opensources.pokmaps"
        minSdk = 37
        targetSdk = 37
        versionCode = appVersionCode
        versionName = appVersionName
    }

    signingConfigs {
        if (releaseKeystore.isPresent) {
            create("release") {
                storeFile = file(releaseKeystore.get())
                storePassword = providers.environmentVariable("POKEMAPS_KEYSTORE_PASSWORD").orNull
                keyAlias = providers.environmentVariable("POKEMAPS_KEY_ALIAS").orNull
                keyPassword = providers.environmentVariable("POKEMAPS_KEY_PASSWORD").orNull
            }
        }
    }

    buildTypes {
        debug {
            applicationIdSuffix = ".debug"
            versionNameSuffix = "-debug"
        }
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            signingConfig = signingConfigs.findByName("release")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    lint {
        abortOnError = true
        checkDependencies = true
        // Les mises à jour de dépendances sont suivies à la main, pas par la CI.
        disable += setOf("GradleDependency", "AndroidGradlePluginVersion", "NewerVersionAvailable")
    }
}

ksp {
    // Schéma exporté par Room : PokedexSchemaTest le compare à la base générée par tools/build_data.py.
    arg("room.schemaLocation", layout.buildDirectory.dir("room-schemas").get().asFile.path)
}

tasks.withType<Test>().configureEach {
    systemProperty("pokemaps.roomSchemas", layout.buildDirectory.dir("room-schemas").get().asFile.path)
    systemProperty("pokemaps.database", file("src/main/assets/database/pokedex.db").path)
}

dependencies {
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.navigation.compose)
    implementation(libs.androidx.hilt.navigation.compose)
    implementation(libs.androidx.room.runtime)
    implementation(libs.androidx.room.ktx)
    implementation(libs.androidx.datastore.preferences)
    implementation(libs.hilt.android)
    implementation(libs.mapcompose)
    ksp(libs.hilt.compiler)
    ksp(libs.androidx.room.compiler)
    debugImplementation(libs.androidx.compose.ui.tooling)

    testImplementation(libs.junit)
    testImplementation(libs.kotlinx.coroutines.test)
    testImplementation(libs.sqlite.jdbc)
    testImplementation(libs.gson)
}

// L'application doit fonctionner sans services Google Play (GrapheneOS) :
// la build échoue si une dépendance en tire une.
val forbiddenGroups =
    listOf(
        "com.google.android.gms",
        "com.google.firebase",
        "com.google.android.play"
    )
val configurationContainer = configurations

tasks.register("checkNoGoogleServices") {
    group = "verification"
    description = "Vérifie qu'aucune dépendance ne dépend des services Google Play ou de Firebase."
    val modules =
        provider {
            configurationContainer
                .getByName("releaseRuntimeClasspath")
                .incoming.resolutionResult.allComponents
                .mapNotNull { it.id as? ModuleComponentIdentifier }
                .map { "${it.group}:${it.module}:${it.version}" }
                .sorted()
        }
    inputs.property("modules", modules)
    doLast {
        val offending = modules.get().filter { module -> forbiddenGroups.any { module.startsWith("$it:") } }
        if (offending.isNotEmpty()) {
            throw GradleException(
                "Dépendances Google Play interdites détectées :\n" + offending.joinToString("\n") { " - $it" }
            )
        }
        logger.lifecycle("OK : ${modules.get().size} dépendances, aucune ne dépend des services Google Play.")
    }
}

tasks.named("check") {
    dependsOn("checkNoGoogleServices")
}

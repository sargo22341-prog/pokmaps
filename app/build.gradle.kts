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

    androidResources {
        // Interface en français uniquement : les traductions des bibliothèques (Material, AndroidX) dans les autres
        // langues ne seraient jamais affichées avec nos textes. Elles occupaient l'essentiel de resources.arsc.
        localeFilters += "fr"
    }

    // Bloc chiffré des dépendances réservé à Google Play : inutile hors du Play Store, et illisible pour qui
    // vérifie l'APK publié dans les GitHub Releases.
    dependenciesInfo {
        includeInApk = false
        includeInBundle = false
    }

    testOptions {
        // Tests UI Compose sous Robolectric : ressources, manifeste fusionné et assets (base, sprites, tuiles).
        unitTests.isIncludeAndroidResources = true
    }

    lint {
        abortOnError = true
        checkDependencies = true
        checkAllWarnings = true
        warningsAsErrors = true
    }
}

kotlin {
    compilerOptions {
        // Tout avertissement du compilateur bloque la build (AGENTS.md, règle 10).
        allWarningsAsErrors.set(true)
        // Valeur de retour ignorée d'une fonction marquée @MustUseReturnValue (bibliothèque standard comprise).
        freeCompilerArgs.add("-Xreturn-value-checker=check")
        // extraWarnings reste désactivé : il ne signale rien dans notre code, mais 30 avertissements dans le code
        // généré par Room (CAN_BE_VAL, REDUNDANT_VISIBILITY_MODIFIER), qu'on ne peut ni corriger ni exclure
        // localement ; les faire taire demanderait une suppression globale, interdite par la règle 10.
    }
}

ksp {
    // Schéma exporté par Room : PokedexSchemaTest le compare à la base générée par tools/build_data.py.
    arg("room.schemaLocation", layout.buildDirectory.dir("room-schemas").get().asFile.path)
}

tasks.withType<Test>().configureEach {
    // sqlite-jdbc utilise JNI pour contrôler le schéma de Room dans les tests JVM.
    jvmArgs("--enable-native-access=ALL-UNNAMED")
    // Robolectric (API 37) crée la mémoire partagée de l'application via les descripteurs de fichier du JDK.
    jvmArgs("--add-exports=java.base/jdk.internal.access=ALL-UNNAMED")
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
    implementation(libs.coil.compose)
    implementation(libs.coil.network.okhttp)
    implementation(libs.coil.gif)
    ksp(libs.hilt.compiler)
    ksp(libs.androidx.room.compiler)
    debugImplementation(libs.androidx.compose.ui.tooling)
    // Activité vide déclarée dans le manifeste debug, où les tests Compose affichent un écran seul.
    debugImplementation(libs.androidx.compose.ui.test.manifest)

    testImplementation(libs.junit)
    testImplementation(libs.kotlinx.coroutines.test)
    testImplementation(libs.sqlite.jdbc)
    testImplementation(libs.gson)
    // Tests UI Compose exécutés sur la JVM (Robolectric) : en CI comme en local, sans appareil ni émulateur.
    testImplementation(platform(libs.androidx.compose.bom))
    testImplementation(libs.androidx.compose.ui.test.junit4)
    testImplementation(libs.robolectric)
    // Versions imposées : celles tirées par Compose et Robolectric appellent InputManager.getInstance(), retiré
    // de l'API 37.
    testImplementation(libs.androidx.test.espresso.core)
    testImplementation(libs.androidx.test.core)
    testImplementation(libs.hilt.android.testing)
    kspTest(libs.hilt.compiler)
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

# Compilation et publication

Prérequis : Android SDK 37, JDK 21, Git ; Python 3.11+ pour les contrôles et la génération explicite.
Gradle utilise Temurin 21 via `gradle/gradle-daemon-jvm.properties`.

```powershell
.\gradlew.bat ktlintCheck checkNoGoogleServices lintDebug testDebugUnitTest assembleDebug
python tools/check_assets.py
cd tools
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
```

Le checkout contient les assets nécessaires : aucun téléchargement de contenu Pokémon ni cache de sources
n'est requis. Les dépendances de compilation peuvent nécessiter un téléchargement.
Les tests Compose tournent en JVM avec Robolectric ; une base manquante fait échouer les contrôles.
Les tests `pipeline` sont séparés et se lancent après une mise à jour explicite des données.

La CI et la release vérifient les assets versionnés, sans les régénérer. Le workflow manuel
`data-pipeline.yml` génère depuis les sources épinglées, teste puis assemble un APK debug pour mesurer sa taille.
Son résumé indique durée de génération, taille du cache, des assets et de l'APK. Il ne publie rien.
La CI conserve l'APK debug pendant 14 jours. La release signe uniquement avec les secrets CI.

La publication reste celle du [README](../README.md#publier-une-version) : tag `vMAJEUR.MINEUR.CORRECTIF`
ou déclenchement manuel. Les notes françaises sous `<!-- notes -->` sont publiées puis vidées par le workflow.
Ne jamais vider les notes manuellement, ni ajouter un keystore au dépôt.
Le code Android vaut `MAJEUR × 10000 + MINEUR × 100 + CORRECTIF`.

L'avertissement `Configuration.setVisible(boolean)` vient d'AGP et reste visible ; son origine est documentée
au README. Il doit être réexaminé lors des mises à jour, sans baseline ni suppression globale.
Les règles de contribution et de test sur appareil sont dans [AGENTS.md](../AGENTS.md).

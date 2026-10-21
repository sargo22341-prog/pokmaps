# Compilation et vérifications

Prérequis : Android SDK 37, JDK 21, Git et Python 3.11+. Gradle utilise Temurin 21 via
`gradle/gradle-daemon-jvm.properties`. Installer les dépendances Python épinglées :

```powershell
python -m pip install -r tools/requirements.txt -r tools/requirements-dev.txt
```

## Contrôles locaux

Depuis la racine, lancer les contrôles correspondant à la partie modifiée :

```powershell
python tools/verify.py                         # Python et Android, sans génération de données
python tools/verify.py --scope android         # changement dans l'application uniquement
python tools/verify.py --scope python          # changement dans les outils uniquement
python tools/verify.py --scope python --pipeline # tests supplémentaires des sources déjà préparées
```

Cette commande conserve tous les contrôles ci-dessous, affiche leurs durées et s'arrête au premier échec.
Les tests du pipeline nécessitent les sources locales épinglées ; ils ne téléchargent rien.
Les commandes individuelles restent disponibles :

```powershell
.\gradlew.bat ktlintCheck checkNoGoogleServices lintDebug testDebugUnitTest assembleDebug
python tools/check_assets.py
cd tools
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
```

Le checkout fournit les assets ; seuls les outils et dépendances de compilation peuvent nécessiter
un téléchargement. Les tests Compose utilisent Robolectric en JVM, sans appareil ni émulateur.
Les tests `pipeline` sont exclus par défaut : les lancer après une génération explicite avec
`python -m pytest -q -m pipeline`, depuis `tools/`. Voir le [pipeline](donnees/pipeline.md).

Pour identifier les contrôles coûteux, utiliser `python -m pytest -q --durations=20` dans `tools/`
et `.\gradlew.bat testDebugUnitTest --profile` à la racine. Les rapports Gradle sont dans
`build/reports/profile/`. Un test `UP-TO-DATE` n'a pas été réexécuté ; ajouter `--rerun` juste après
`testDebugUnitTest` pour mesurer son exécution réelle sans recompiler toutes ses dépendances.
Le contrôle Gradle `checkAssets` conserve son résultat dans `app/build/verification/assets.checked` :
Gradle le relance dès qu'une entrée change ou que ce fichier manque. Les empreintes SHA-256 restent
vérifiées intégralement lors de cette exécution. La première lecture de milliers de fichiers peut être
sensiblement plus lente que les suivantes ; comparer des mesures à cache comparable.

L’APK debug est `app/build/outputs/apk/debug/app-debug.apk`, paquet `org.opensources.pokmaps.debug`.
Pour l’installation ADB préservant les données, suivre [AGENTS.md, §10](../AGENTS.md#10-téléphone-et-adb).
`dependencyUpdates` liste les versions stables sans rien modifier ; toute mise à jour reste manuelle.

## CI et publication

| Workflow | Rôle |
|---|---|
| `ci.yml` | Assets, contrôles Python et Android, tests JVM, APK debug conservé 14 jours |
| `release.yml` | Vérifications, signature CI, APK et empreinte SHA-256 dans GitHub Releases |
| `data-pipeline.yml` | Génération et tests des sources épinglées, mesures du cache, des assets et de l’APK |

CI et release utilisent les assets versionnés sans régénération. Le workflow manuel du pipeline
ne publie rien et ne remplace pas la mise à jour locale des assets à versionner.
Son résumé indique la restauration exacte du cache, la durée de génération et des tests de sources,
la taille du cache et des assets, puis la durée d'assemblage et la taille de l'APK debug.
Les cartes DS préparatoires disposent d'un cache distinct, sans clé de repli : toute modification des
scripts Python, des données éditoriales ou des dépendances Python impose leur reconstruction.
Un cache réutilisé passe toujours les validations d'inventaire, de catalogue et de commit source.
Les tests des sources affichent leurs vingt durées les plus longues, y compris les fixtures de génération.
Le cache `tools/.cache/map-renders` conserve les pyramides des générations 1 à 3 et les cadres 3D DS.
Ses entrées sont identifiées par les pixels ou les triangles, textures, cadrage et version du moteur.
Elles vérifient leur intégrité avant réutilisation ; les catalogues, personnages et validations sont recalculés.
La CI restaure ce cache entre commits : chaque entrée décide elle-même si elle est encore applicable.
Le job est borné à 90 minutes pour inclure le rendu DS à cache froid et le test de reconstruction.
Ne pas lancer les lecteurs d'assets ou le build Android pendant une régénération des mêmes fichiers :
les dossiers de cartes sont remplacés pendant l'export. Attendre sa réussite avant les contrôles.
La procédure et les secrets de publication sont dans le [README](../README.md#publier-une-version).

Dépréciation connue : `Configuration.setVisible(boolean)` est appelée par AGP (`BasePlugin`,
`SourceSetManager`). Elle reste visible avec `org.gradle.warning.mode=all` ; la réexaminer lors
des mises à jour d’AGP et avant le retrait de cette API dans Gradle 11. Aucun masquage ni baseline.

Lint 32.4.1 se rabat sur tout le module quand les sources principales d'un modèle de test sont absentes.
Il parcourt alors aussi les assets et les sorties de build. `app/build.gradle.kts` fournit aux seules tâches
d'analyse des tests un dossier principal explicitement vide, via les entrées internes d'AGP 9.4.1.
Ce recours local est nécessaire car le modèle est généré à l'intérieur de l'action Lint ; les sources de test,
dépendances et règles restent intactes. Une modification du modèle AGP incompatible fait échouer ce contrôle.

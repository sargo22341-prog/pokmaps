# AGENTS.md

Règles obligatoires du dépôt **Pokémaps**. Ce fichier fait autorité ; `.claude/CLAUDE.md` ne fait
que l'importer. Le lire entièrement, puis lire le code et les documents concernés avant toute
modification. `README.md` présente l'application, ses sources de données et la procédure de
publication. Ce fichier ne dépasse pas 400 lignes.

---

## 0. Règles de base

Dix règles inspirées de *The Power of 10* (G. Holzmann, NASA/JPL), réécrites pour valoir en Kotlin
comme en Python. Chacune donne son **intention** : c'est elle qui fait foi. Les exemples entre
parenthèses illustrent, ils ne limitent pas. Ces règles valent pour tout le code, existant comme
nouveau, de production comme de test, public comme privé.

Le but commun : un code prévisible, qu'un outil peut vérifier et qu'un humain relit vite.

1. **Flux de contrôle simple et exhaustif.** Pas de récursion dans le code applicatif sans borne
   démontrée (profondeur d'une chaîne d'évolution, par exemple). Un choix sur un ensemble fermé
   (`enum`, `sealed`) traite tous les cas explicitement, sans `else` fourre-tout. Sortir tôt plutôt
   qu'imbriquer.
   *Intention :* chaque chemin est visible, et le compilateur signale le cas oublié.
2. **Tout ce qui répète ou attend a une borne.** Une tentative a un nombre maximal, une attente
   (réseau, disque, processus) a un délai, un téléchargement a une taille maximale, un parcours a
   un plafond. Une boucle sans fin n'est admise que si elle est annulable. Toute coroutine meurt
   avec le scope qui l'a lancée (`viewModelScope`, jamais `GlobalScope`).
   *Intention :* le programme ne peut ni tourner, ni attendre, ni consommer indéfiniment.
3. **Rien de lourd dans les chemins chauds.** Pas de requête Room, d'E/S, de décodage d'image ni de
   calcul coûteux dans un composable, un `Canvas` ou le fil principal. Les calculs dérivés se font
   dans le ViewModel ou le domaine, hors du rendu. Une optimisation se mesure, elle ne se suppose pas.
   *Intention :* la carte et les listes restent fluides, de façon prévisible.
4. **Une fonction tient sur un écran.** Au plus **60 lignes**, quel que soit son rôle ou sa
   visibilité : logique, composable, fonction privée, script Python. Au-delà, extraire des
   sous-fonctions nommées par ce qu'elles font. Un fichier a une seule responsabilité et reste
   sous **600 lignes** (§4).
   *Intention :* une unité de code se comprend en une lecture, sans défilement.
5. **Des états impossibles plutôt que des vérifications.** Utiliser `sealed interface`, `enum`,
   `data class` immuables et dataclasses Python pour qu'un état invalide ne puisse pas exister.
   Toute donnée extérieure (source téléchargée, CSV de `tools/data`, base embarquée, préférence)
   est validée une fois, à la frontière, puis considérée comme sûre.
   *Intention :* les invariants sont garantis par construction, pas espérés à l'exécution.
6. **Portée et mutabilité minimales.** `private` ou `internal` par défaut ; `val` plutôt que `var` ;
   un `MutableStateFlow` n'est exposé qu'en `StateFlow`. En Python, préfixer `_` ce qui est interne
   au module.
   *Intention :* on sait toujours qui peut lire et qui peut modifier une donnée.
7. **Aucune erreur silencieuse.** Une erreur est traitée, transformée ou propagée, jamais avalée.
   `CancellationException` est toujours relancée avant une capture générique. Chaque échec devient
   un état visible (`failed`, `Error`), distinct d'un résultat vide. En Python, un échec de
   génération ou de validation arrête le build avec un message qui nomme la donnée fautive.
   *Intention :* un problème se voit là où il survient, jamais plus tard sous une autre forme.
8. **Pas de magie.** Réflexion, métaprogrammation et logique de build astucieuse seulement sur
   nécessité démontrée. Exceptions admises et délimitées : Hilt, Room et Compose via leurs
   compilateurs (KSP, plugin Compose). Pas de nouvelle génération de code ni de bibliothèque à
   réflexion sans justification écrite.
   *Intention :* ce que fait le programme se lit dans son source.
9. **Dépendances à sens unique, sans raccourci.** Le sens des couches est fixé au §3 ; jamais
   inversé, jamais sauté. Pas de longues chaînes d'accès ni de rappels imbriqués.
   *Intention :* une donnée a un chemin unique et évident, et chaque couche se teste seule.
10. **Zéro avertissement, zéro passe-droit muet.** Compilateur Kotlin, Android Lint, ktlint, Ruff
    et pytest sont réglés au plus strict et leurs avertissements bloquent. Toute exclusion
    (`@Suppress`, `# noqa`, `tools:ignore`) est locale et porte un commentaire qui la justifie.
    Aucune suppression globale ni baseline pour faire passer un build.
    *Intention :* l'outil voit tout ce qu'il peut voir, et rien n'est ignoré sans raison écrite.

---

## 1. Le projet

Application Android de cartes interactives et de Pokédex pour **Pokémon Rouge, Bleu, Jaune, Or, Argent et Cristal**,
conçue pour accueillir ensuite d'autres jeux. Carte et Pokédex sont liés dans les deux sens.

- Package : `org.opensources.pokmaps` ; le debug s'installe sous `org.opensources.pokmaps.debug`.
- **100 % hors ligne** : base `pokedex.db`, cartes et sprites sont générés par `tools/` et embarqués
  dans les assets, ainsi que les guides et listes de succès. Exception explicitement demandée : connexion
  facultative à RetroAchievements, uniquement en lecture et sur synchronisation manuelle dans les Réglages.
  La clé reste chiffrée localement, exclue des sauvegardes ; aucun succès n'est modifié.
- Interface **en français uniquement** : tout texte visible vient de `res/values/strings.xml`.
- Distribution par GitHub Releases uniquement, usage personnel, pas de Play Store.
- Ne rien récupérer de pokemaps.net : utiliser les mêmes sources que lui (`README.md`).
- Ne pas laisser de bug connu, de `TODO`, de `FIXME` ni de dette volontaire. Ne pas sur-concevoir :
  le code le plus simple qui répond au besoin est le bon.

---

## 2. Stack et dépendances

| Élément | Choix |
|---|---|
| Langage | Kotlin (application), Python 3.11+ (génération des données) |
| UI | Jetpack Compose + Material 3, Navigation Compose |
| `minSdk` = `targetSdk` = `compileSdk` | **37 (Android 17)**, sans rétrocompatibilité |
| Données | Room en **lecture seule** sur la base générée, DataStore pour les préférences |
| Injection | Hilt (KSP) |
| Carte et images | MapCompose, Coil 3 |
| Build | AGP 9 + Gradle, versions dans `gradle/libs.versions.toml` |

- **Aucun service Google Play** : ni GMS, ni Firebase, ni Google Maps, ni Play Core. L'application
  doit fonctionner sur GrapheneOS. `checkNoGoogleServices` le vérifie ; si une bibliothèque tire
  GMS, elle est écartée, pas contournée.
- Ajouter une dépendance seulement si elle remplace un vrai volume de code, et la justifier dans le
  rapport. Toute version passe par `gradle/libs.versions.toml`, jamais en dur.
- Utiliser directement les API Android 17 : pas de `Build.VERSION`, pas de compat superflue.
- Mises à jour : `.\gradlew.bat dependencyUpdates` liste les versions stables sans rien modifier ;
  toute montée de version reste manuelle et passe les contrôles du §8. C'est pourquoi les contrôles
  Lint de versions publiées (`AndroidGradlePluginVersion`, `GradleDependency`,
  `NewerVersionAvailable`) sont désactivés dans `app/build.gradle.kts` : seule exception globale
  admise à la règle 10, car leur résultat dépend du jour du build, pas du dépôt.
- Python : dépendances épinglées dans `tools/requirements.txt` et `tools/requirements-dev.txt`.

---

## 3. Architecture

Sens de dépendance strict, jamais inversé :

```
ui (Composable → ViewModel) → domain/usecase → data/repository → data/db (Room) · data/settings
                                    ↓                 ↓
                     domain (model, map, pokemon, pokedex) : modèles et règles pures
```

- Un composable n'accède **jamais** à Room, à DataStore, aux assets ni à un repository. Il reçoit
  un état et remonte des événements par lambdas.
- Un ViewModel ne dépend que de `domain` (cas d'usage et modèles), jamais de `data`.
- `domain/usecase` est le seul pont vers `data`. Pas d'interface de repository tant qu'une seule
  implémentation existe et qu'un test n'en a pas besoin.
- `domain/model`, `domain/map`, `domain/pokemon` et `domain/pokedex` sont du Kotlin pur : aucune
  classe Android, aucun import de `data`. Ils se testent en JVM pur.
- `data` peut utiliser les modèles du domaine ; les entités Room (`Entities.kt`, `Rows.kt`) ne
  sortent pas de `data`.
- `di/` assemble les dépendances, sans logique métier.

---

## 4. Organisation des dossiers et des fichiers

Le code est rangé **par couche, puis par thème**. Ne créer un dossier que s'il clarifie une
responsabilité réelle.

| Chemin | Responsabilité |
|---|---|
| `app/src/main/java/.../ui/<écran>/` | Écran, ViewModel, `UiState` et composants propres à cet écran |
| `app/src/main/java/.../ui/common/` | Composants utilisés par **au moins deux** écrans |
| `app/src/main/java/.../ui/theme/` | Couleurs, typographie et thème Material |
| `app/src/main/java/.../domain/<sujet>/` | Modèles et règles pures : `map`, `pokemon`, `pokedex`, `model` |
| `app/src/main/java/.../domain/usecase/` | Cas d'usage appelés par les ViewModels |
| `app/src/main/java/.../data/<sujet>/` | `db` (Room), `repository`, `settings` (DataStore), `map` (tuiles) |
| `app/src/main/java/.../di/` | Modules Hilt |
| `app/src/main/res/` | Ressources Android, textes et thèmes |
| `app/src/test/java/...` | Tests JVM, **dans le même paquet** que le code testé |
| `tools/pokemaps_data/` | Sources, transformations, assemblage et validation des données |
| `tools/data/` | Corrections éditoriales maintenues à la main (CSV) |
| `tools/spot_editor/` | Éditeur PC des emplacements sauvages (Tk), lancé par `tools/map_editor.py` |
| `tools/tests/` | Tests du pipeline Python |

Écrans existants dans `ui/` : `about`, `character`, `game`, `item`, `map`, `move`, `place`, `pokedex`,
`pokemon`, `search`, `settings`. Un nouvel écran crée son dossier ; un nouveau sujet métier crée
son dossier dans `domain`.

Taille et découpage :

- **Aucun fichier source ne dépasse 600 lignes** (Kotlin, Python, tests compris). Découper dès
  ~400 lignes ; viser moins de 250.
- **Aucune fonction ne dépasse 60 lignes** (règle 4), privée comme publique.
- Lignes de 120 caractères au plus (`.editorconfig`, Ruff). Écrire du code lisible, pas compacté
  pour passer sous une limite.
- Découper **par responsabilité**, jamais par tranches arbitraires. Exemples existants :
  `PokemonScreen.kt` (structure de l'écran) et `PokemonSections.kt` (sections de contenu) ;
  `pret.py` (façade), `pret_maps.py` (parsing des cartes), `pret_models.py` (modèles).
- Un fichier porte le nom de sa responsabilité (`MapOverlayRenderer.kt`, `builder_maps.py`).
- **Interdits** : `utils`, `helpers`, `misc`, `shared`, `managers`, `base`, `ext` et équivalents.
  `ui/common` n'accueille que du code réellement partagé ; un composant qui ne sert qu'un écran
  retourne dans le dossier de cet écran.
- Pas de duplication : factoriser dès la deuxième copie réelle. Pas d'abstraction prématurée.
- Ne pas déplacer ni renommer de nombreux fichiers sans lien avec la demande.

---

## 5. Conventions de code

**Écrans.** Chaque écran expose, dans le même fichier :

```kotlin
@Composable
fun PokemonRoute(...)          // récupère le ViewModel et collecte l'état

@Composable
fun PokemonScreen(             // sans état : reçoit l'UiState, remonte les intentions
    state: PokemonUiState,
    onAction: (PokemonAction) -> Unit,
)
```

La version sans état ne connaît ni ViewModel, ni `Context`, ni repository. Les grands écrans sont
découpés en sections nommées (`Header`, `StatsSection`…) de moins de 60 lignes chacune.

**État.** Un `XxxUiState` immuable par écran, exposé en `StateFlow`. Chargement, contenu, **vide**
et **erreur** sont distincts : une liste vide n'est pas une erreur. Les propriétés dérivées vivent
sur l'`UiState`, pas dans le composable. Collecter avec `collectAsStateWithLifecycle`.

**Coroutines.** `viewModelScope` dans les ViewModels ; E/S sur `Dispatchers.IO` via les
repositories ; pas de `runBlocking` hors tests. Le motif « relancer `CancellationException`, puis
marquer l'état en échec » s'écrit une seule fois par fichier et se réutilise.

**Kotlin.** Pas de `!!` en production, pas de `lateinit` évitable, `when` exhaustif sur les types
fermés. Pas de fonction d'extension « pratique » déposée hors de son domaine.

**Compose.** Clés stables dans les listes paresseuses ; `stringResource` pour tout texte visible ;
couleurs via `MaterialTheme.colorScheme` ; `contentDescription` sur toute image porteuse de sens ;
zones tactiles d'au moins 48 dp.

**Python.** Annotations de type sur toute fonction ; dataclasses (`frozen=True` si possible) pour
les données ; pas d'état global mutable ; `pathlib` pour les chemins ; aucune capture `except`
générique sans `raise`.

**Commentaires.** Rares, en français comme le code existant, et qui expliquent le *pourquoi*.
Suivre la densité de commentaires du code voisin.

---

## 6. Génération des données

### Données externes

Les données et ressources finales récupérées ou produites depuis des sources externes sont stockées dans le dépôt.
Les builds et publications utilisent ces assets versionnés, même si les sources deviennent indisponibles.
La génération est explicite ; caches et sources brutes restent hors de Git, sans Git LFS.

- `tools/build_data.py` est le point d'entrée explicite pour modifier les données ; jamais lancé par un build Android.
- `tools/pokemaps_data/` sépare sources (`sources.py`, `pret_source.py`), lecture (`pokeapi.py`,
  `pret*.py`), assemblage (`builder*.py`, `maps*.py`, `sprites.py`) et validation (`validate.py`).
- Les corrections maintenues à la main restent dans `tools/data/`, jamais dans les sorties générées.
- Génération reproductible : sources épinglées (commits, versions), téléchargements bornés en
  temps et en taille, validations explicites, erreurs visibles.
- Toute modification d'une table, de `schema.sql` ou d'un asset généré met à jour la validation et
  son test, et garde `PokedexSchemaTest` vert (schéma Room = base générée).
- Versionner les assets finaux et leur inventaire `assets.sha256`, jamais les caches (`tools/.cache`) ni les sources brutes.

---

## 7. Tests

- Tests JVM dans `app/src/test`, **dans le même paquet** que le code testé ; tests du pipeline
  dans `tools/tests`.
- Couvrir les règles pures du domaine, les cas d'usage, les ViewModels, les conversions et les cas
  limites concernés. Chaque ViewModel modifié teste au moins ses états vide et erreur.
- Un défaut corrigé et reproductible = un test de non-régression.
- Les tests ne dépendent jamais du réseau réel ni de données externes variables. Les tests Python
  ordinaires utilisent les assets versionnés ; les tests marqués `pipeline` réutilisent les sources épinglées
  préparées par `build_data.py`, uniquement lors d'une mise à jour explicite des données.
- Utiliser des faux en mémoire plutôt qu'un framework de mock supplémentaire.
- Quand un test échoue, corriger le **code**, pas l'attente du test, sauf si l'attente est fausse,
  et le dire.

---

## 8. Vérifications avant de déclarer une tâche terminée

Lancer ce qui couvre la partie touchée ; tout doit passer :

```powershell
# Android
.\gradlew.bat ktlintCheck checkNoGoogleServices lintDebug testDebugUnitTest assembleDebug

# Python (sans génération ni cache)
python tools/check_assets.py
cd tools; ruff check .; ruff format --check .; python -m pytest -q
# Après modification des données : génération explicite, puis tests des sources
python -m pytest -q -m pipeline
```

- Zéro erreur, zéro avertissement : Kotlin (`allWarningsAsErrors`), Lint (`checkAllWarnings`,
  `warningsAsErrors`), ktlint, Ruff, pytest (`filterwarnings = error`).
- Vérifier les limites de 600 lignes par fichier et 60 lignes par fonction sur les fichiers
  touchés, puis relire le diff complet.
- `.\gradlew.bat ktlintFormat` corrige le style ; ne pas formater des fichiers hors de la tâche.
- Ne pas lancer de build lourd sans que la tâche le demande ou que ce soit nécessaire.
- Ne jamais annoncer une vérification non exécutée ni masquer un échec. Corriger la cause, ne pas
  empiler de contournement.

---

## 9. Notes de version et publication

- Toute modification visible de l'application ajoute **une courte phrase française** dans
  `RELEASE_NOTES.md`, sous `<!-- notes -->`, au format `- …`, dans le même changement.
- Un changement purement interne (outils, tests, documentation, CI) n'exige pas de note.
- Ne jamais toucher à l'en-tête ni au marqueur ; ne jamais vider la liste à la main.
- `.github/workflows/release.yml` publie ces notes dans la GitHub Release puis vide la liste.
- La release se déclenche par un tag `vMAJEUR.MINEUR.CORRECTIF` ou par lancement manuel.
- Le build release est signé uniquement avec les secrets CI ; aucun keystore ni mot de passe dans
  Git, et l'agent ne les demande jamais.
- Garder la procédure de publication cohérente avec `README.md`.

---

## 10. Téléphone et ADB

**ADB** : `C:\platform-tools\adb.exe`. Un téléphone peut être branché pour les tests.

- Vérifier d'abord que l'appareil est visible (`adb devices`). Ne jamais supposer une connexion ni
  prétendre avoir testé si ADB ne le voit pas.
- Installer par-dessus, ce qui préserve les données :
  ```powershell
  .\gradlew.bat assembleDebug
  C:\platform-tools\adb.exe install -r -d app\build\outputs\apk\debug\app-debug.apk
  C:\platform-tools\adb.exe shell am start -n org.opensources.pokmaps.debug/org.opensources.pokmaps.MainActivity
  ```
- **Interdits sans demande explicite** : `adb uninstall`, `pm clear`, `connectedDebugAndroidTest`
  (il désinstalle l'application et efface ses données).
- En cas de problème, consulter `logcat` filtré sur le package, sans jamais recopier de secret.

---

## 11. Git et fichiers

- Modifier uniquement les fichiers liés à la tâche ; petits changements cohérents.
- **Aucun commit sans demande explicite.** Jamais de `git reset --hard` ni de suppression de travail
  existant pour résoudre un conflit.
- Ne pas versionner : `build/`, `local.properties`, caches, sources brutes téléchargées, secrets, keystores,
  binaires générés hors assets attendus.
- Fichiers temporaires de session : dans le scratchpad, jamais à la racine du dépôt.
- Mettre à jour la documentation (`README.md`) qui décrit un comportement modifié.

---

## 12. Rapport final

Le rapport indique :

- résumé des changements et fichiers principaux modifiés ;
- contrôles exécutés et leurs résultats ;
- contrôles non lancés ou restants, dits clairement, sans prétendre qu'ils ont réussi ;
- tout incident ou échec, y compris non bloquant ;
- un **message de commit copiable en français**, si des changements ont été faits.

Avant de donner le rapport, tenter **une seule fois** (adapter le message) :

```powershell
kdeconnect-cli --device 9d3e0da7eb0e4cacb95ff4869f8f669b --ping-msg "Pokémaps : tâche terminée"
```

Ignorer sa sortie : l'appareil est souvent injoignable. Ne pas relancer en boucle ni chercher un
autre canal ; un échec se mentionne en une ligne dans le rapport.

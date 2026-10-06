# Pokémaps

Application Android de **cartes interactives pour Pokémon Rouge, Bleu et Jaune**, entièrement en français :
carte de Kanto, Pokémon de chaque lieu, fiches Pokémon (évolutions, attaques, CT/CS) et Pokédex.

- Kotlin + Jetpack Compose, **Android 17 (API 37) minimum**
- **Aucun service Google Play** : l'application fonctionne sur GrapheneOS
- 100 % hors-ligne : toutes les données sont embarquées dans une base SQLite (seul l'artwork officiel
  d'un Pokémon, affiché à la demande, est chargé en ligne)
- Identifiant de l'application : `org.opensources.pokmaps`

## Captures d'écran

| Carte et Pokémon sauvages | Pokédex | Fiche Pokémon | Lieux d'un Pokémon |
|---|---|---|---|
| ![Forêt de Jade sur la carte, avec ses Pokémon sauvages](docs/screenshots/carte.webp) | ![Pokédex de Pokémon Rouge](docs/screenshots/pokedex.webp) | ![Fiche de Pikachu](docs/screenshots/pokemon.webp) | ![Lieux de Pikachu surlignés sur la carte de Kanto](docs/screenshots/lieux-pokemon.webp) |

Pokémon Rouge, sur l'émulateur Android 17 (Pixel 9 Pro XL).

## Structure

| Dossier | Contenu |
|---|---|
| `app/` | Application Android |
| `tools/` | Pipeline de données Python : génère la base `pokedex.db` et les images |
| `tools/data/` | Corrections relues à la main (noms français, notes, doublons) |
| `docs/screenshots/` | Captures d'écran du README |
| `.github/` | CI/CD (GitHub Actions) |

## Données

`tools/build_data.py` génère, dans `app/src/main/assets/` :

- `database/pokedex.db` : la base SQLite de l'application ;
- `sprites/` : icônes de boîte des Pokémon, sprites des jeux, sprites animés et icônes d'objets ;
- `maps/` : cartes pixel-art de chaque jeu découpées en tuiles (carte du monde de Kanto et cartes intérieures),
  et sprites des PNJ.

Toutes les images sont embarquées en WebP sans perte, plus léger que PNG et GIF à pixels identiques ; chaque
image convertie est relue et comparée à sa source, et la génération s'arrête si elle diffère.

Sources (les mêmes que [pokemaps.net](https://pokemaps.net)) :

- **[PokéAPI](https://pokeapi.co)**, via l'export CSV du dépôt [PokeAPI/pokeapi](https://github.com/PokeAPI/pokeapi) :
  Pokémon, noms et descriptions en français, types et stats par génération, attaques par jeu, évolutions, Pokédex,
  lieux et rencontres de chaque version. Les CSV sont téléchargés une seule fois au build, avec cache ;
  l'application n'appelle jamais l'API ([usage équitable](https://pokeapi.co/docs/v2#fairuse)).
- **[pokesprite](https://github.com/msikma/pokesprite)** : icônes de boîte des Pokémon et icônes d'objets.
- **[PokeAPI/sprites](https://github.com/PokeAPI/sprites)** : sprites de Rouge/Bleu et Jaune, et sprites animés
  de Noir/Blanc (activables dans les Réglages).
- **[pret/pokered](https://github.com/pret/pokered)** et **[pret/pokeyellow](https://github.com/pret/pokeyellow)**
  (désassemblages des jeux) : uniquement pour dessiner les cartes, à partir des blocs, tilesets, palettes Super Game Boy,
  connexions, warps, objets et PNJ. Aucune ROM n'est utilisée.
- **`tools/data/`** : quelques corrections et compléments relus à la main (accents, étages mal nommés,
  prix du Casino, Pokémon demandés en échange, doublons), noms français des cartes (`maps.csv`), des classes de
  dresseurs (`trainer_classes.csv`) et des personnages (`npc_names.csv`), et lien entre cartes et zones de
  rencontre PokéAPI (`map_areas.csv`).

Les sources sont figées sur des commits précis (`tools/pokemaps_data/sources.py`), la génération est donc
reproductible. La base est vérifiée après chaque génération (références cohérentes, probabilités de rencontre
qui totalisent 100 %, chaque Pokémon obtenable…).

Les jeux pris en charge sont listés dans `tools/pokemaps_data/games.py`. Ajouter un jeu (Or/Argent, par
exemple) demande :

- une ligne dans `games.py` : Pokémon, attaques, objets et rencontres sont alors extraits de PokéAPI ;
- de nommer ses nouvelles classes de dresseurs et ses nouveaux personnages dans `tools/data/` (un nom
  manquant arrête la génération) ;
- d'adapter la lecture des cartes pret (`pret*.py`, écrite pour la 1re génération), la carte du monde
  (`maps_layout.py` : `WORLD`, `START_MAP`) et les palettes (`maps_render.py`) ;
- de classer ses nouvelles méthodes de rencontre (ex. `headbutt`) dans `ObtainMethod` : une méthode inconnue
  fait échouer le chargement au lieu de disparaître en silence des filtres et de la carte.

Les données générées ne sont pas versionnées : elles sont produites par la CI, ou en local avec la commande
ci-dessous.

## Compiler en local

Prérequis : JDK 21, Android SDK (API 37), Python 3.11 ou plus récent, git.

```bash
# 1. Générer la base de données, les images et les cartes (télécharge les sources dans tools/.cache)
pip install -r tools/requirements.txt
python3 tools/build_data.py

# 2. Compiler et installer l'APK debug
./gradlew installDebug
```

Vérifications lancées par la CI :

```bash
./gradlew ktlintCheck checkNoGoogleServices lintDebug testDebugUnitTest   # Android (tests UI compris)
./gradlew ktlintFormat                                                    # corrige le style Kotlin

cd tools
pip install -r requirements-dev.txt
ruff check . && ruff format --check .   # style Python
python -m pytest                        # tests du pipeline
```

Les tests Python réutilisent les sources épinglées préparées par `tools/build_data.py` et bloquent tout accès
réseau. Générer les données avant de lancer `pytest` localement.

Les tests UI Compose tournent sur la JVM avec Robolectric, dans `testDebugUnitTest` : ni appareil ni émulateur.
Ils parcourent l'application complète sur la base générée (Pokédex → fiche → carte, recherche → lieu ou objet,
choix du jeu, réglages) et sont ignorés si elle n'a pas été générée.

`checkNoGoogleServices` fait échouer la build si une dépendance tire les services Google Play
(`com.google.android.gms`), Firebase ou Play Core.

### Dépendances et notes de version

`.\gradlew.bat dependencyUpdates` liste les versions stables disponibles sans modifier le
catalogue. Toute mise à jour reste manuelle et doit être vérifiée avec les contrôles du projet.

Pour une prochaine release, ajouter une ligne française sous le marqueur `<!-- notes -->` dans
[`RELEASE_NOTES.md`](RELEASE_NOTES.md). Le workflow inclut ces notes dans la GitHub Release et,
après publication réussie, vide la liste dans un commit sur `main`. Si `main` contient déjà des
notes différentes de celles du tag, elles sont conservées pour la release suivante.

## CI/CD

- **CI** (`.github/workflows/ci.yml`), à chaque push et pull request : génération et tests des données,
  ktlint, vérification sans Google Play, Android Lint, tests unitaires et APK debug
  (téléchargeable dans les artefacts du workflow pendant 14 jours).
- **Release** (`.github/workflows/release.yml`), à chaque tag `vX.Y.Z` : APK release signé publié dans
  [GitHub Releases](../../releases), avec son empreinte SHA-256.

### Publier une version

**Une seule fois** : créer la clé de signature et l'ajouter aux secrets du dépôt.

```bash
keytool -genkeypair -v -keystore pokemaps-release.jks -alias pokemaps \
  -keyalg RSA -keysize 4096 -validity 10000
base64 -w 0 pokemaps-release.jks > pokemaps-release.jks.base64
```

Dans GitHub, *Settings → Secrets and variables → Actions → New repository secret* :

| Secret | Valeur |
|---|---|
| `KEYSTORE_BASE64` | contenu de `pokemaps-release.jks.base64` |
| `KEYSTORE_PASSWORD` | mot de passe du keystore |
| `KEY_ALIAS` | `pokemaps` |
| `KEY_PASSWORD` | mot de passe de la clé |

⚠️ Conservez `pokemaps-release.jks` et ses mots de passe en lieu sûr, **hors du dépôt** : sans eux, il est
impossible de publier une mise à jour installable par-dessus l'application existante.

**À chaque version**, au choix :

- pousser un tag :
  ```bash
  git tag v1.0.0
  git push origin v1.0.0
  ```
- ou, dans GitHub, *Actions → Release → Run workflow* en indiquant la version (ex. `1.0.0`) : le tag est créé
  sur le dernier commit de la branche choisie.

Le code de version Android est calculé à partir du tag : `MAJEUR × 10000 + MINEUR × 100 + CORRECTIF`.

## Installer sur GrapheneOS (Obtainium)

[Obtainium](https://github.com/ImranR98/Obtainium) installe et met à jour les applications directement
depuis leurs GitHub Releases.

1. Installer Obtainium (depuis ses GitHub Releases ou F-Droid).
2. *Ajouter une application* → URL : `https://github.com/sargo22341-prog/pokmaps`.
3. Obtainium installe la dernière version et signale les mises à jour.

Sans Obtainium : télécharger l'APK depuis la page Releases et l'ouvrir sur le téléphone.

## Mentions légales

Projet de fan, personnel et non commercial. Pokémon et les noms associés sont des marques de Nintendo,
Game Freak et The Pokémon Company ; les images des Pokémon, des objets et des cartes sont © Nintendo, Creatures
et GAME FREAK. Ce dépôt ne contient aucune ROM ni ressource extraite d'une ROM.
Le code de l'application est sous licence [MIT](LICENSE).

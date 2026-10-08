# Pokémaps

Application Android de **cartes interactives pour Pokémon Rouge, Bleu, Jaune, Or, Argent et Cristal**, en français :
cartes de Kanto et de Johto, Pokémon de chaque lieu, fiches Pokémon (évolutions, attaques, CT/CS, chromatique), fiches des
attaques (effet et probabilité de l'effet) et Pokédex.

- Kotlin + Jetpack Compose, **Android 17 (API 37) minimum**
- **Aucun service Google Play** : l'application fonctionne sur GrapheneOS
- 100 % hors-ligne : toutes les données sont embarquées dans une base SQLite et les assets ; l'application n'a pas
  la permission Internet
- Identifiant de l'application : `org.opensources.pokmaps`

Le jeu se choisit dans l'onglet « Jeu » de la barre du bas, classé par génération, et reste mémorisé. Dans les
Réglages, « Captures comptées » fait compter un Pokémon capturé pour le jeu choisi, pour sa génération ou pour tous
les jeux ; chaque capture reste mémorisée dans le jeu où elle a été cochée, si bien que changer ce réglage ne perd
rien.

Or, Argent et Cristal proposent les cartes de Johto et de Kanto : les boutons de région permettent de passer de l'une à
l'autre. Les filtres Matin, Jour et Nuit de la carte sont tous activés par défaut ; ils filtrent les marqueurs et
la liste du lieu sélectionné. Chaque rencontre précise aussi ses conditions (heure, essaim, concours…). Les
cartes conservent les couleurs de jour du jeu, indépendamment de ce filtre. Coup d'Boule et Éclate-Roc placent les
Pokémon sur les arbres et les rochers correspondants.

Les fiches d'Or et d'Argent affichent les six statistiques, les objets tenus, le sexe, les groupes d'œufs,
les cycles d'éclosion et les attaques par œuf. Les évolutions précisent le bonheur, l'heure et les objets tenus.
Le calculateur de capture reproduit la formule et les Balls du jeu, avec ses défauts d'origine ; le niveau du
Pokémon de l'équipe, la pêche et le contexte de la Love Ball sont réglables. Cristal ajoute ses cartes (Tour de Combat,
salles des Ruines d'Alpha, Sanctuaire du Dragon), ses rencontres et échanges, les sept possibilités de l'œuf de la
Pension, Suicune à la Tour Ferraille et les attaques par tuteur. Le tuteur coûte 4 000 jetons ; les récompenses de
Buena affichent leur prix en points de la Carte Bleue.

## Captures d'écran

| Carte et Pokémon sauvages | Pokédex | Fiche Pokémon | Lieux d'un Pokémon |
|---|---|---|---|
| ![Forêt de Jade sur la carte, avec ses Pokémon sauvages](docs/screenshots/carte.webp) | ![Pokédex de Pokémon Rouge](docs/screenshots/pokedex.webp) | ![Fiche de Pikachu](docs/screenshots/pokemon.webp) | ![Lieux de Pikachu surlignés sur la carte de Kanto](docs/screenshots/lieux-pokemon.webp) |

Pokémon Rouge, sur l'émulateur Android 17 (Pixel 9 Pro XL).

| Carte de Johto dans Pokémon Cristal |
|---|
| ![Bourg Geon sur la carte de Johto, dans Pokémon Cristal](docs/screenshots/johto.webp) |

Pokémon Cristal, sur le même émulateur Android 17 (Pixel 9 Pro XL).

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
- `sprites/` : sprites des Pokémon (un seul style partout, animé ou fixe, normal ou chromatique) et icônes
  d'objets ;
- `maps/` : cartes pixel-art de chaque jeu découpées en tuiles (cartes du monde de Kanto et de Johto et lieux à part),
  et sprites des PNJ.

Les jeux en cours d'intégration (`GAMES_IN_PROGRESS` dans `tools/pokemaps_data/games.py`, actuellement vide)
ne sont pas embarqués : `tools/build_data.py` les génère avec tous les autres dans un aperçu,
`tools/build/preview/` (même organisation, hors de Git), validé de la même façon. Les tests et l'éditeur des
emplacements le lisent.

Toutes les images sont embarquées en WebP sans perte, plus léger que PNG et GIF à pixels identiques ; chaque
image convertie est relue et comparée à sa source, et la génération s'arrête si elle diffère.

Sources (les mêmes que [pokemaps.net](https://pokemaps.net)) :

- **[PokéAPI](https://pokeapi.co)**, via l'export CSV du dépôt [PokeAPI/pokeapi](https://github.com/PokeAPI/pokeapi) :
  Pokémon, noms et descriptions en français, types et stats par génération, attaques par jeu, évolutions, Pokédex,
  lieux et rencontres de chaque version ; objets tenus, groupes d'œufs et talents, préparés pour les générations
  suivantes (vides en 1re génération). Les CSV sont téléchargés une seule fois au build, avec cache ;
  l'application n'appelle jamais l'API ([usage équitable](https://pokeapi.co/docs/v2#fairuse)).
- **[pokesprite](https://github.com/msikma/pokesprite)** : icônes d'objets.
- **[PokeAPI/sprites](https://github.com/PokeAPI/sprites)** : sprites animés de Noir/Blanc, normaux et chromatiques,
  seul style de sprite des Pokémon (carte, listes, fiches, Pokédex, évolutions, jaquettes dessinées de l'écran de
  choix du jeu). Le sprite fixe est la première image du sprite animé : même
  dessin, même taille. Les Réglages choisissent, endroit par endroit, où ils sont animés. Ces sprites n'existent que
  pour les Pokémon n° 1 à 649 (5 premières générations) : la génération s'arrête si un jeu en demande d'autres.
- **[pret/pokered](https://github.com/pret/pokered)** et **[pret/pokeyellow](https://github.com/pret/pokeyellow)**
  (désassemblages des jeux) : pour dessiner les cartes, à partir des blocs, tilesets, palettes Super Game Boy,
  connexions, warps, objets et PNJ, et ce que proposent les personnages (soins, boutiques, dons, échanges,
  lots du Casino et leur prix en jetons, distributeurs, fossiles ranimés) ; pour l'effet de chaque attaque, tel que
  le moteur de combat l'exécute (`data/moves/moves.asm`). Aucune ROM n'est utilisée.
- **[pret/pokegold](https://github.com/pret/pokegold)** (Or et Argent) et
  **[pret/pokecrystal](https://github.com/pret/pokecrystal)** (Cristal) : cartes de Johto et de Kanto, et rencontres
  aléatoires lues comme le moteur les tire (herbes et grottes par moment de la journée, surf, pêche, Coup d'Boule,
  Éclate-Roc, essaims, Concours de capture d'insectes, `data/wild/`), PokéAPI les décrivant mal pour ces jeux
  (moments de la journée perdus, emplacements d'essaim manquants) ; dons, Pokémon fixes et échanges restent ceux de
  PokéAPI.
- **`tools/data/`** : quelques corrections et compléments relus à la main (accents, étages mal nommés,
  prix du Casino, Pokémon demandés en échange, doublons), noms français des cartes (`maps.csv`), des classes de
  dresseurs (`trainer_classes.csv`), des personnages et leur apparence (`npc_names.csv`, `npc_text_names.csv`) et
  des installations (`facility_names.csv`), lien entre cartes et zones de rencontre PokéAPI, par famille de cartes
  (`map_areas.csv`), zones et objets absents de PokéAPI (`extra_areas.csv`, `extra_items.csv` : l'ADN Berzerk
  et les lettres d'Or et d'Argent), Pokémon qu'un jeu n'obtient que par échange avec un autre (`transfer_only.csv`),
  personnages en double écartés (`npc_duplicates.csv` : un même personnage à plusieurs étapes du scénario), offres
  que les scripts ne disent pas simplement (`npc_offers.csv`, action `add` : échanges d'objets, jetons vendus,
  Pokémon de départ du labo du Prof. Chen, Balls de Fargas ; action `remove` : don qu'un autre personnage fait
  pendant la scène), texte de l'effet de chaque attaque (`move_effects.csv`, une ligne par effet du moteur ou par
  attaque particulière, avec sa probabilité en chances sur 256 relevée dans `engine/battle/effects.asm`) et placement
  des cartes là où les connexions ne suffisent pas : cartes ancrées dans une carte du monde (`map_anchors.csv`),
  connexions incohérentes écartées (`map_connection_skips.csv`) et ville ou route d'origine d'une carte atteinte de
  plusieurs côtés (`map_parents.csv`).

Les sources sont figées sur des commits précis (`tools/pokemaps_data/sources.py`), la génération est donc
reproductible. La base est vérifiée après chaque génération (références cohérentes, probabilités de rencontre
qui totalisent 100 % pour chaque moment de la journée, chaque Pokémon obtenable par rencontre, évolution ou
reproduction…).

### Ajouter un jeu

Les jeux pris en charge sont listés dans `tools/pokemaps_data/games.py`. Ajouter un jeu demande :

- une ligne dans `games.py`, d'abord dans `GAMES_IN_PROGRESS` (le jeu est généré et validé dans l'aperçu sans entrer
  dans l'application), puis dans `GAMES` quand l'application sait l'afficher : Pokémon, attaques, objets et
  rencontres sont alors extraits de PokéAPI (avec les
  symboles pret qui distinguent ses versions, comme `_RED` et `_BLUE` pour les lots du Casino), et la jaquette de
  chaque version (`VersionCover` : Pokémon de la jaquette et couleur) ;
- une source de sprites pour ses Pokémon au-delà du n° 649 (`sprites.py`), s'il en a ;
- de nommer ses nouvelles classes de dresseurs et ses nouveaux personnages dans `tools/data/` (un nom
  manquant arrête la génération) ;
- de choisir ou d'adapter son lecteur pret (`PretFormat`, `pret*.py`, `pret_gen2*.py`), ses régions et villes
  de départ (`Game.regions`), ses palettes et son rendu (`maps_render*.py`) ;
- de vérifier ses variantes de format même s’il partage un lecteur : Cristal ajoute une seconde banque
  de tuiles, des scripts conditionnels et `warpfacing`, ainsi que des tables sauvages `map_id` ;
- de lire et valider ses nouvelles offres (ex. tuteur payé en jetons et récompenses de Buena payées en
  points), puis de les représenter dans les modèles du domaine et les ressources françaises ;
- de classer ses nouvelles méthodes de rencontre (ex. `headbutt`) dans `ObtainMethod` : une méthode inconnue
  fait échouer le chargement au lieu de disparaître en silence des filtres et de la carte ;
- de lire les effets de ses attaques (`pret_moves.py`, `pret_gen2_moves.py` et `move_effects.csv`) : une
  attaque sans effet arrête la génération.

Les mécaniques propres aux générations suivantes sont prévues, et la fiche d'un Pokémon les affiche dès qu'un jeu les
connaît (`GenerationFeature` dans l'application) : objets tenus (2e génération ; PokéAPI ne les donne qu'à partir de la
3e, ceux de la 2e sont lus dans pret), chromatiques (1 chance sur 8 192, puis 1 sur 4 096 à partir
de la 6e génération), sexe, groupes d'œufs et cycles d'éclosion (2e génération) et talents, dont le talent caché
(3e et 5e générations). `tools/tests/test_future_generations.py` vérifie ces tables sur des jeux plus récents.

Les données générées ne sont pas versionnées : elles sont produites par la CI, ou en local avec la commande
ci-dessous.

## Éditeur des emplacements sauvages

Après une génération des données, lancer `python tools/map_editor.py` sur le PC. Tant que des jeux sont en cours
d'intégration, l'éditeur lit l'aperçu de tous les jeux (`tools/build/preview/`), sinon les assets de l'application.
Choisir les jeux (Rouge, Bleu et Jaune sont édités ensemble), la région (Johto ou Kanto pour Or et Argent ; un
bâtiment est rangé dans la région de la ville ou route d'où l'on y entre), la route ou le lieu, puis le terrain :
herbes ou sol pour la marche, eau pour le surf et la pêche, arbres pour Coup d'Boule et rochers pour Éclate-Roc (2e
génération). Seuls les lieux qui ont des rencontres sauvages sont proposés, et seuls les terrains où le jeu fait apparaître un
Pokémon : les herbes si la carte en a, le sol uniquement dans les grottes et bâtiments (pas dehors, ni dans la forêt de
Jade ou le Parc Safari, où la marche ne compte que dans les herbes), l'eau s'il y a du surf ou de la pêche, les arbres et
rochers seulement dans les cartes où le jeu en fait tomber ou surgir des Pokémon. La génération
applique la même règle et refuse dans `map_spots.csv` un terrain où aucun Pokémon ne peut apparaître. La liste affiche les
Pokémon à placer sur ce terrain, avec leur version, leurs niveaux et leur probabilité. Cliquer sur la carte ajoute un
emplacement, centré sur la case de 16 px ; cliquer sur un emplacement le retire. « Vider ce terrain » retire tous ses
emplacements.

Les cases « Afficher sur la carte » dessinent, à la taille de l'application, ce que la carte finale montre autour des
emplacements : entrées, objets et objets cachés, dresseurs, personnages et installations, Pokémon fixes. L'« aperçu des
Pokémon sauvages » (décoché par défaut) pose un sprite du terrain sur chaque emplacement pour juger la place qu'ils
prennent ; l'application, elle, choisit elle-même quel Pokémon va sur quel emplacement. L'éditeur lit les sources pret
déjà téléchargées dans `tools/.cache` par la génération.

Un avertissement apparaît quand un terrain a moins d'emplacements que de Pokémon à y dessiner (dans la version qui en
demande le plus) : l'application les rangerait alors en grille au milieu du terrain. L'enregistrement demande une
confirmation s'il reste de tels terrains.

Les positions sont communes à tous les jeux d'une même famille de cartes (`map_family` dans
`tools/pokemaps_data/games.py`) : Or, Argent et Cristal ont leur propre famille, et leurs emplacements ne se
mélangent pas à ceux de Rouge, Bleu et Jaune. Seuls les terrains réellement modifiés sont écrits dans `tools/data/map_spots.csv`
(colonnes `family,map_identifier,kind,x,y`, une ligne sans coordonnées pour un terrain vide) ; les autres restent
calculés par la génération. Le bouton « Enregistrer toutes les cartes » écrit ensemble les modifications de tous les
lieux, puis lance `tools/build_data.py`, Ruff et les tests Python. Si Ruff ou pytest manque dans le Python qui exécute
l'éditeur, leurs dépendances épinglées sont installées depuis `tools/requirements-dev.txt`. Une confirmation apparaît
après la réussite de toutes les étapes ; une fenêtre d'erreur précise l'étape et la sortie en cas d'échec.

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

Les deux workflows réutilisent le cache `tools/.cache` : CSV PokéAPI, sprites, sources de pokered,
pokeyellow, pokegold et pokecrystal, et conversions WebP. La clé dépend des commits épinglés dans
`sources.py` et du convertisseur `webp.py`. Le résumé de chaque exécution indique la durée de génération
des données et la taille exacte de l'APK produit (debug en CI, signé en release).

Mesure locale du 8 octobre 2026, avec les six versions et les sources déjà en cache : génération et validation
en 50,7 s ; APK debug de 62 760 138 octets (59,85 Mio). Les cartes représentent 5 903 Kio pour 5 732 tuiles.
Ces mesures Windows ne prédisent pas la durée d'un premier téléchargement ni la taille de l'APK release.

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

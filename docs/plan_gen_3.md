# Plan — Génération 3 (Rubis, Saphir, Émeraude, Rouge Feu, Vert Feuille)

Plan de travail pour ajouter la 3e génération à Pokémaps, construit sur ce qui a été fait pour les
générations 1 et 2 (commits « Gen 2 (phases 0 à 3) » → « phase 8 », `docs/generations/bilan-generations-1-2.md`).
Chaque phase se termine par les contrôles de `AGENTS.md` §8, sans avertissement, et ne laisse aucun `TODO`.
Les cases se cochent au fil de l'eau ; une décision prise se note dans la section « Décisions ».

Rappel du principe hérité de la génération 2 : un jeu entre d'abord dans `GAMES_IN_PROGRESS`
(`tools/pokemaps_data/games.py`), il est généré et validé dans l'aperçu `tools/build/preview/`, puis il passe
dans `GAMES` seulement quand l'application sait tout afficher.

---

## Deux branches : Hoenn et Remake 1G

La 3e génération réunit deux ensembles de jeux qui ne partagent que le moteur GBA. Ils se traitent **comme deux
générations différentes** : ne jamais supposer qu'un fait de l'un vaut pour l'autre.

| | **Branche Hoenn** | **Branche Remake 1G** |
|---|---|---|
| Jeux (groupes PokéAPI) | Rubis, Saphir (`ruby-sapphire`, 5) ; Émeraude (`emerald`, 6) | Rouge Feu, Vert Feuille (`firered-leafgreen`, 7) |
| Désassemblages pret | `pokeruby`, `pokeemerald` | `pokefirered` |
| Famille de cartes | `ruby-sapphire-emerald` | `firered-leafgreen` (aucun partage avec `red-blue-yellow`) |
| Régions | Hoenn (+ monde sous-marin) | Kanto, Îles Sevii |
| Pokédex du jeu | Hoenn (202), puis National (386) | Kanto (151), puis National (386) |
| Propre à la branche | Plongée, marées, Baies, Concours, Pokéblocs, Bases Secrètes, Zone de Combat (E) | Îles Sevii, Ruines Tanoby, Cherche VS, Memorydex |

**Choix du jeu** : la section « 3e génération » affiche la ligne Rubis / Saphir / Émeraude, puis, en dessous,
une ligne titrée « Remake 1G » avec Rouge Feu / Vert Feuille (aujourd'hui `GameUiState.byGeneration` groupe par
`generationId` seulement).

Communs aux deux branches : format pret `GEN3` (lecteurs avec variantes par dépôt), formule de capture, talents,
natures, IV, sprites des espèces 252 à 386.

---

## État de départ (constaté le 9 octobre 2026)

- PokéAPI épinglée (`sources.py`) connaît déjà les groupes `ruby-sapphire` (5), `emerald` (6),
  `firered-leafgreen` (7) et les versions 7 à 11 (Rubis, Saphir, Émeraude, Rouge Feu, Vert Feuille).
  `colosseum` et `xd` existent aussi mais n'ont ni carte ni désassemblage : **hors périmètre**.
- Méthodes de rencontre PokéAPI présentes en 3e génération et **inconnues de l'application** (`ObtainMethod`
  lèverait une exception) : `seaweed` (Plongée), `roaming-water`, `devon-scope`, `wailmer-pail`,
  `feebas-tile-fishing`, `colosseum-bonus-disc-jpn`, `colosseum-bonus-disc-us`, `pokemon-channel-pal`.
- Méthode d'apprentissage `light-ball-egg` (Émeraude, Électacle de Pichu) : `PokemonRepository` ne lit que
  `level-up`, `machine`, `egg`, `tutor` → elle disparaîtrait **en silence** (règle 7).
- PokéAPI n'a aucune condition horaire pour la 3e génération (normal : pas de matin/jour/nuit en jeu), mais
  a des conditions de scénario (`story-progress-hall-of-fame`, fossiles, starters…).
- `pokedex_version_groups` : Rubis/Saphir/Émeraude → Pokédex de Hoenn, Rouge Feu/Vert Feuille → Pokédex de
  Kanto (151). Aucun lien vers le Pokédex National : les espèces de Johto des Îles Sevii et du Parc Safari
  d'Émeraude n'ont donc aucun Pokédex. La base sait déjà relier plusieurs Pokédex à un groupe
  (`version_group_pokedex`), mais chaque jeu actuel n'en a qu'un.
- Tables déjà prêtes (vides jusqu'ici) : talents (`pokemon_ability`, `ability_version_group`), objets tenus
  via PokéAPI à partir de la 3e génération (`builder_items._pokeapi_held_items`), `test_future_generations.py`.
- Sprites Noir/Blanc disponibles jusqu'au n° 649 : les n° 252 à 386 sont couverts. Les 28 formes de Zarbi
  (dont ! et ?) sont déjà embarquées (`sprites/unown`, 112 fichiers).
- Classes de dégâts par type jusqu'à la 3e génération : déjà gérées (`builder_moves._damage_class`).

### Valeurs codées en dur pour les générations 1-2 (à généraliser)

| Endroit | Hypothèse actuelle |
|---|---|
| `ui/game/GameViewModel.kt` (`byGeneration`) | une section par génération ; pas de ligne « Remake 1G » |
| `ui/map/MapScreen.kt` (l. 119-204) | `generationId >= 2` ⇒ moments de la journée, voile de lumière, calque Baies |
| `ui/map/MapViewModel.kt` (l. 160) | « même génération » ⇒ même région ; faux entre Émeraude et Rouge Feu |
| `ui/pokemon/PokemonScreen.kt` (l. 61, 109, 132) | Zarbi et onglets œuf/tuteur selon `generationId >= 2` |
| `domain/pokemon/Gen2CatchRate.kt` | `CaptureGeneration` : seulement GEN1/GEN2 ; `from(3)` = null ⇒ calculateur masqué |
| `domain/pokemon/CatchRate.kt` | `Ball` sans Filet, Scuba, Faiblo, Bis, Chrono, Luxe, Honor Ball |
| `domain/guide/CaptureGoal.kt` | `require(species in 1..251)`, objectifs par identifiant de succès |
| `domain/guide/Roamers.kt` | routes de Johto, Raikou/Entei/Suicune uniquement |
| `domain/guide/CollectionBackup.kt` | versions `1..6`, errants `4..6` |
| `data/settings/BackupJson.kt` | versions `1..6`, `<= 251` espèces, `<= 26` formes de Zarbi |
| `data/settings/CollectionBackupRepository.kt` | boucle `for (version in 1..6)` |
| `data/settings/GuideSettings.kt` | `versionId in 1..6`, errants `4..6` |
| `domain/guide/RetroProgress.kt` | `RetroGames.ids` : six jeux |
| `domain/guide/Guide.kt` | `unownGoal` : trois identifiants de succès |
| `ui/guide/GuideViewModel.kt` (l. 66) | objectif Zarbi = 26 |
| `ui/guide/GuideScreen.kt` (l. 50) | outil de bonheur : `versionId == 6` (Cristal) |
| `domain/usecase/BreedingUseCase.kt` | `require(game.generationId == 2)` (DV) |
| `data/guide/GuideDefinition.kt` | `KANTO_VERSIONS` / `JOHTO_VERSIONS`, sources éditoriales |
| `data/guide/AchievementGuides.kt` | six listes, ordre `version <= 3` |
| `tools/pokemaps_data/maps.py` | `GEN2_ROAMING_AREA = "roaming-johto/area"` |
| `tools/pokemaps_data/games.py` | `PretFormat` GEN1/GEN2, `ONE_OFF_METHODS` |
| `tools/pokemaps_data/sprites.py` | icône d'objet trouvée seulement par le numéro de 8e génération |
| `tools/spot_editor/version_choice.py` | `_VERSION_LABELS` des quatre groupes actuels |
| `res/values/strings.xml` `about_credit_pret` | cite seulement pokered et pokeyellow (déjà incomplet) |
| `AGENTS.md` §1, `README.md`, `docs/` | listent les six jeux actuels |

---

## Décisions (prises en phase 0, le 9 octobre 2026)

- [x] **Deux branches.** Hoenn (Rubis, Saphir, Émeraude) et Remake 1G (Rouge Feu, Vert Feuille) se traitent
      comme deux générations distinctes (section « Deux branches »). Le choix du jeu affiche « 3e génération »
      puis, en dessous, la ligne « Remake 1G ».
- [x] **Ordre d'intégration.** Branche Hoenn d'abord : Émeraude (pokeemerald, le désassemblage le plus abouti),
      puis Rubis/Saphir (pokeruby, variante de la même famille, comme Cristal après Or/Argent). Branche Remake 1G
      ensuite : Rouge Feu/Vert Feuille (pokefirered).
- [x] **Familles de cartes** : `ruby-sapphire-emerald` et `firered-leafgreen`. Rubis et Émeraude partagent
      348 identifiants de carte, mais 113 ont des blocs différents (27 de taille différente, dont Routes 103 et
      109) : les emplacements propres à un jeu utilisent la colonne `version_group` de `map_spots.csv`, déjà
      prévue pour Or/Argent et Cristal.
- [x] **Source des rencontres aléatoires** : `src/data/wild_encounters.json` de pret, lu comme le moteur, relié
      directement aux constantes de carte (`map`). PokéAPI garde dons, fixes, échanges et errants. Un test compare
      les deux sources pour signaler les écarts.
- [x] **Pokédex affiché : comme dans les jeux.** Chaque jeu a son Pokédex régional (Hoenn 202, Kanto 151, ordre
      régional) puis le Pokédex National (1 à 386), que le jeu débloque : Émeraude par le Prof. Seko après la
      Ligue (`LittlerootTown_ProfessorBirchsLab`), Rouge Feu/Vert Feuille par le Prof. Chen
      (`PalletTown_ProfessorOaksLab`), Rubis/Saphir par l'échange d'un Pokémon hors Hoenn (`src/pokemon_3.c`).
      Conditions exactes à relire dans pret en phase 5. Le National est ajouté à la génération (absent de
      `pokedex_version_groups` pour ces groupes).
- [x] **Îles Sevii** : une seule région « Îles Sevii ». Les îles forment 7 ensembles non reliés (Îles 1, 2, 3,
      5, 6, 7 reliées chacune à leurs routes, Île 4 seule) placés par `map_anchors.csv`. Les cartes
      `PROTOTYPE_SEVII_ISLE_6/7`, reliées à l'Île 3 mais inutilisées, sont écartées (`map_connection_skips.csv`).
- [x] **Monde sous-marin (Plongée)** : niveau « Sous l'eau » de la carte du monde de Hoenn (sélecteur d'étage).
      Les cartes `Underwater_*` sont reliées à la surface par les connexions `dive` / `emerge` de `map.json`
      (14 dans Émeraude, 8 dans Rubis) et ont la taille de la route qu'elles doublent.
- [x] **`SHOAL_CAVE` et ses marées** : deux niveaux, marée haute (`ShoalCave_HighTide*`) et marée basse
      (`ShoalCave_LowTide*`).
- [x] **Contenus d'événement** (Île Lointaine, Île Aurore, Roc Nombri, Billet Éon, e-Reader, Mystery
      Gift, Pokémon Box, Colosseum) : affichés avec la mention « événement externe », sans compter dans les
      objectifs de capture. Les méthodes `colosseum-bonus-disc-*` et `pokemon-channel-pal` suivent la même règle.
- [x] **Zone de Combat / Pyramide / Butte d'Entraînement (Émeraude)** : cartes affichées, contenu aléatoire
      non simulé, ce qui n'est pas listé est dit explicitement. Les rencontres de la Pyramide et du Battle Pike (nom français à relire)
      (`gBattlePyramidWildMonHeaders`, `gBattlePikeWildMonHeaders`) sont lisibles et seront listées par série.
- [x] **Décorations des Bases Secrètes** : dans le périmètre. Nouvelle entité lue dans pret
      (`src/data/decoration/`), noms français dans un CSV relu (absentes de PokéAPI).
- [x] **Concours, Pokéblocs et Baies** : dans le périmètre de cette intégration (phase 8). Arbres à baies
      seulement dans la branche Hoenn (Rouge Feu/Vert Feuille n'en a pas).
- [x] **Revanches** (Match Call / PokéNav d'Émeraude `gRematchTable`, Cherche VS de Rubis/Saphir
      `gTrainerEyeTrainers`, Cherche VS de Rouge Feu/Vert Feuille `sRematches`) : toutes les équipes du dresseur,
      dans l'ordre, avec leur condition.
- [x] **Formes** : Deoxys dans la forme du jeu (Normale Rubis/Saphir, Vitesse Émeraude, Attaque Rouge Feu,
      Défense Vert Feuille) ;
      Morphéo avec ses 4 formes listées ; Spinda en une seule fiche (motif aléatoire, non listé).
- [x] **Budget de taille** : pas de plafond fixe pour l'APK, qui dépassera 100 Mio avec les générations et
      remakes à venir. En revanche, aucun fichier disproportionné : images en tuiles WebP de 256 px, pas de vidéo
      ni d'audio, tout asset unitaire de plus de 5 Mio signalé et justifié (le plus gros aujourd'hui :
      `pokedex.db`, 3,3 Mio). Taille de l'APK, des cartes et du dépôt Git mesurée et rapportée à chaque phase ;
      estimation : +35 à +60 Mio.
- [x] **Jaquettes** : Groudon `0xA8243A` (Rubis), Kyogre `0x2F4FB0` (Saphir), Rayquaza `0x2E9A5A` (Émeraude),
      Dracaufeu `0xE8642A` (Rouge Feu), Florizarre `0x6DB33F` (Vert Feuille), à relire à l'écran en phase 6.

---

## Phase 0 — Reconnaissance des sources et cadrage

- [x] Choisir et épingler les commits de `pret/pokeruby`, `pret/pokeemerald`, `pret/pokefirered` dans
      `PRET_COMMITS` (`sources.py`) ; vérifier la licence et l'absence de ROM nécessaire pour lire les données.
- [x] Mesurer la taille d'un `git fetch --depth 1` de chaque dépôt ; adapter le délai de `fetch_pret`
      (120 s) avec une borne explicite, et la clé de cache CI (`.github/actions/build-database/action.yml`,
      `data-pipeline.yml`).
- [x] Recenser dans chaque dépôt, et noter dans ce plan, les fichiers à lire et leurs variantes :
  - [x] cartes : `data/maps/<Carte>/map.json`, `data/maps/map_groups.json`, `data/layouts/layouts.json`,
        `map.bin`, `border.bin` ;
  - [x] tilesets : `data/tilesets/{primary,secondary}/<nom>/tiles.png`, `palettes/*.pal`, `metatiles.bin`,
        `metatile_attributes.bin`, tables de tilesets (`src/data/tilesets/headers.h`) ;
  - [x] comportements de cases : `include/constants/metatile_behaviors.h`, `src/metatile_behavior.c`
        (`MetatileBehavior_IsLandWildEncounter`, `…IsWaterWildEncounter`, Plongée) ;
  - [x] rencontres : `src/data/wild_encounters.json` (ou son équivalent dans pokeruby) ;
  - [x] dresseurs : `src/data/trainers.h`, `src/data/trainer_parties.h`, classes et revanches ;
  - [x] attaques : `src/data/battle_moves.h` (effet, probabilité), `data/battle_scripts_1.s` ;
  - [x] objets, Pokémon de base (objets tenus), échanges (`src/data/trade.h`), tuteurs, errants
        (`src/roamer.c`), baies (`src/berry.c`), scripts (`data/maps/*/scripts.inc`, `data/scripts/*.inc`) ;
  - [x] sprites des PNJ : `graphics/object_events/pics/**` et leurs palettes.
- [x] Identifier comment chaque dépôt distingue ses versions (`#if` de compilation pour Rubis/Saphir,
      Rouge Feu/Vert Feuille, suffixes des tables de rencontres) ; fixer les symboles de `pret_versions`.
- [x] Vérifier les icônes pokesprite des objets de la 3e génération (baies, Balls, objets clés) et lister
      les manquants.
- [x] Prendre les décisions de la section précédente et mettre à jour ce plan.

### Résultats de la reconnaissance

**Commits épinglés** (`PRET_COMMITS`, 9 octobre 2026) :

| Dépôt | Commit | Date | `fetch --depth 1` | Paquet | Sources | Fichiers |
|---|---|---|---|---|---|---|
| `pokeruby` | `5784633ce4ef` | 28/09/2026 | 3 s | 9,4 Mio | 45 Mio | 9 783 |
| `pokeemerald` | `731ad5bfd6e6` | 01/10/2026 | 2 s | 12 Mio | 60 Mio | 11 557 |
| `pokefirered` | `037335f4c725` | 26/09/2026 | 1 s | 9,4 Mio | 45 Mio | 9 857 |

- Délai de chaque commande git : borne nommée `PRET_GIT_TIMEOUT_SECONDS = 120`, gardée (marge de plus de 20×).
  La clé du cache CI dépend déjà de `sources.py` : l'ajout des commits l'invalide sans autre changement.
  `build_data.py` récupère tous les dépôts épinglés, y compris ceux qu'aucun jeu ne lit encore.
- **Licence** : aucun des trois dépôts n'a de fichier de licence, comme pokered à pokecrystal. Même usage que
  pour les générations 1-2 : lecture des données de jeu, crédit dans « À propos » (`about_credit_pret`).
- **Aucune ROM** : ni `baserom` dans les Makefile ou `INSTALL.md`. Tout ce qu'il faut lire est en source :
  `map.json`, `.bin`, `tiles.png` indexés, palettes JASC, JSON de rencontres, en-têtes C, scripts `.inc`.

**Cartes.** `map.json` par carte (394 Rubis, 518 Émeraude, 425 Rouge Feu), `map_groups.json`,
`data/layouts/layouts.json` (`blockdata_filepath` → `map.bin`, `border_filepath` → `border.bin`).

- Champs d'événements : `object_events`, `warp_events`, `coord_events` (`trigger`, et `weather` dans la branche
  Hoenn), `bg_events` de type `sign`, `hidden_item` (`item`, `flag`) et `secret_base` (Hoenn).
- Variantes Remake 1G : `object_events[].type` (`object` ou `clone` : 9 clones à ignorer), `floor_number`,
  `bg_events` caché avec `quantity` et `underfoot`, bordures de taille variable (`border_width`,
  `border_height`), pas de connexion `dive`.
- Variantes Hoenn : connexions `dive` / `emerge`, `shared_events_map` / `shared_scripts_map` (35 cartes Rubis,
  50 Émeraude), noms des cartes sous-marines différents (`Underwater1..4` dans Rubis, `Underwater_Route124…`
  dans Émeraude).
- Ensembles reliés par connexions : Hoenn 49 cartes depuis `LITTLEROOT_TOWN` (Émeraude comme Rubis), plus le
  Parc Safari (6 cartes Émeraude, 4 Rubis), le monde sous-marin (4) et l'extérieur de la Zone de Combat (2) ;
  Kanto de Rouge Feu 38 cartes depuis `PALLET_TOWN`, plus les 7 ensembles des Îles Sevii.
- Surface totale des layouts : Émeraude 83 Mpx, Rubis 65 Mpx, Rouge Feu 62 Mpx, contre 38 Mpx pour Cristal
  (5,3 Mio de tuiles) et 24 Mpx pour Rouge.

**Tilesets.** `data/tilesets/{primary,secondary}/<nom>/` : `tiles.png` (indexé, 4 bpp), `palettes/00.pal` à
`15.pal` (JASC), `metatiles.bin` (8 tuiles par métatile, deux couches), `metatile_attributes.bin`, `anim/`.

| | Rubis/Saphir | Émeraude | Rouge Feu/Vert Feuille |
|---|---|---|---|
| Tables de tilesets | `data/tilesets/headers.inc` (assembleur), graphismes dans `src/data/graphics.c` | `src/data/tilesets/headers.h` | `src/data/tilesets/headers.h` |
| Tilesets primaires / secondaires | 3 / 50 | 3 / 67 | 2 / 66 |
| Primaire : tuiles, métatiles, palettes | 512, 512, 0-5 | 512, 512, 0-5 | 640, 640, **0-6** |
| Attributs par métatile | u16 : comportement (bits 0-7), couche (12-15) | idem | **u32** : comportement (0-8), terrain (9-13), type de rencontre (24-26), couche (29-30) |

**Comportements de cases.** `include/constants/metatile_behaviors.h` : `#define MB_…` (Rubis, Rouge Feu) ou
`enum` (Émeraude). Hoenn : la rencontre se décide par le comportement (`MetatileBehavior_IsLandWildEncounter`,
`…IsWaterWildEncounter`, `IsEncounterTile` dans `src/metatile_behavior.c`). Remake 1G : par le champ
« type de rencontre » de l'attribut (`TILE_ENCOUNTER_LAND` / `WATER`, `src/wild_encounter.c`), pas par le
comportement.

**Rencontres.** `src/data/wild_encounters.json` dans les trois dépôts, champs `land_mons` (12 emplacements),
`water_mons` (5), `rock_smash_mons` (5), `fishing_mons` (10 : Canne 0-1, Super Canne 2-4, Méga Canne 5-9), taux
identiques. Les cartes sous-marines utilisent `water_mons`. Émeraude ajoute deux groupes hors cartes (Pyramide,
Battle Pike).

**Distinction des versions.** Symboles retenus pour `pret_versions` :

| Jeu | Symboles | Rencontres | Scripts et C |
|---|---|---|---|
| Rubis / Saphir | `("ruby", "RUBY")`, `("sapphire", "SAPPHIRE")` | suffixes `_Ruby` / `_Sapphire` (97 + 97) | `#ifdef SAPPHIRE` (518 en C, 84 `.ifdef` en scripts) |
| Émeraude | `("emerald", "EMERALD")` | sans suffixe | aucun `#if` de version |
| Rouge Feu / Vert Feuille | `("firered", "FIRERED")`, `("leafgreen", "LEAFGREEN")` | suffixes `_FireRed` / `_LeafGreen` (132 + 132) | `#if defined(FIRERED)`, `.ifdef FIRERED` / `LEAFGREEN` |

Autres conditions à figer à la lecture : `ENGLISH` (pokeruby a aussi `GERMAN`), `REVISION` 0, `DEBUG` 0,
`BUGFIX` / `UBFIX` / `MODERN` absents ; toute autre condition arrête la lecture.

**Autres données** (chemin et variantes par dépôt) :

| Donnée | Rubis/Saphir | Émeraude | Rouge Feu/Vert Feuille |
|---|---|---|---|
| Dresseurs | `src/data/trainers_en.h` | `src/data/trainers.h` | `src/data/trainers.h` (macros `NO_ITEM_CUSTOM_MOVES(…)`) |
| Équipes | `trainer_parties.h` (`.level`, attaques sans accolades) | `trainer_parties.h` (`.lvl`, `{…}`) | idem Émeraude |
| Revanches | `gTrainerEyeTrainers` (`src/battle_setup.c`) | `gRematchTable` (`src/battle_setup.c`) | `sRematches` (`src/vs_seeker.c`) |
| Attaques | `src/data/battle_moves.c` | `src/data/battle_moves.h` | `src/data/battle_moves.h` ; tous : `data/battle_scripts_1.s` |
| Objets | `src/data/items_en.h` | `src/data/items.h` | `src/data/items.json` |
| Pokémon de base | `src/data/pokemon/base_stats.h` | `src/data/pokemon/species_info.h` | `species_info.h` |
| Échanges | `gIngameTrades` (`src/trade.c`) | `src/data/trade.h` | `src/data/ingame_trades.h` |
| Tuteurs | aucun | `tutor_learnsets.h`, `src/field_specials.c` | `tutor_learnsets.h`, `src/field_specials.c` |
| Errants | `sRoamerLocations[][6]` (`src/roamer.c`) | `[][6]` | `[][7]` |
| Baies | `src/berry.c`, arbres initiaux `setberrytree` (80) dans `data/scripts/new_game.inc` | idem | `src/berry.c`, pas d'arbre |
| Scripts | `data/maps/*/scripts.inc` (370) + `text.inc`, `data/scripts/` (35) | `scripts.inc` (468), `data/scripts/` (57) | `scripts.inc` (425) + `text.inc`, `data/scripts/` (39) |
| Drapeaux, variables | `include/constants/flags.h`, `vars.h` | idem | idem |
| PNJ | `graphics/object_events/pics/` (224 images, 27 palettes) | 253 images, 36 palettes | 157 images, 19 palettes |
| Tables PNJ | `src/data/object_events/object_event_{graphics_info,pic_tables,graphics}.h` | idem | idem |
| Sections de la carte régionale | `src/data/region_map/region_map_sections.json` | idem | idem |

**Icônes d'objets.** 309 objets de la 3e génération, dont 58 CT/CS (icône par type, déjà gérée). 33 objets
n'ont pas d'icône par le numéro de 8e génération : Multi Exp, Cherche VS, les 12 Lettres (Lettre Oranj …
Lettre Retro), Pack Devon, Boîte Pokéblocs, Clés Salle 1/2/4/6, Bon Commande, Memorydex, Sac à Baies, TV ABC,
Tri-Passe, Passe Prisme, Ticketmystik, Ticketaurora, Pot Poudre, Rubis, Saphir, Sceau Magma, Vieillecarte.
**Tous existent dans pokesprite** sous `items/<catégorie>/<identifiant>.png` : la phase 1 ajoute cette
recherche par identifiant, ce qui donne aussi son icône à la Multi Exp (déjà sans icône en 2e génération) et
remplace le repli de `bike-voucher`.

## Phase 1 — Données Pokémon (PokéAPI) dans l'aperçu

Communs :

- [x] `games.py` : `PretFormat.GEN3`, jeux `RUBY_SAPPHIRE`, `EMERALD`, `FIRERED_LEAFGREEN` (`GEN3_GAMES`) avec leurs
      `VersionCover`, les symboles de `pret_versions` fixés en phase 0 et `national_dex`. Ils restent **hors de
      `GAMES_IN_PROGRESS`** (décision du 9 octobre 2026) : l'aperçu génère aussi cartes, rencontres pret et effets
      d'attaques de chaque jeu en cours, que lisent seulement les phases 2 à 4. Ils y entrent avec le lecteur pret
      GEN3 ; d'ici là, `open_pret` et `read_pret_moves` refusent explicitement le format GEN3, et les tests
      construisent leurs tables de Pokémon avec la fixture `gen3_builder`.
- [x] `ONE_OFF_METHODS` : `roaming-water`, `devon-scope`, `wailmer-pail`, et `feebas-tile-fishing` (statué : rencontre
      unique, car 50 % sur six cases tirées au hasard ne complètent aucune table ; note dans `encounter_curation.csv`).
- [x] Événements externes (`games.EXTERNAL_EVENT_METHODS` : `colosseum-bonus-disc-*`, `pokemon-channel-pal` ;
      `EXTERNAL_EVENT_LOCATIONS` : Roc Nombri, Île Aurore, Île Lointaine, Île du Sud) : rencontres gardées avec
      la note « Événement externe », exclues de l'obtention dans `validate._check_obtainable`. Lugia et Ho-Oh, qui
      ne sont qu'au Roc Nombri, passent dans `transfer_only.csv` (Colosseum, XD).
- [x] Espèces 252 à 386 : stats, types, talents (aucun talent caché), objets tenus (PokéAPI ; Pikachu ne tient rien
      dans Rouge Feu/Vert Feuille, comme dans pokefirered), groupes d'œufs, évolutions. Schéma 13 : `evolution` gagne
      `min_beauty` (Barpau), `relative_physical_stats` (Debugant, perdu jusqu'ici en 2e génération) et
      `personality_chance` (Chenipotte) ; Munja garde son déclencheur `shed`. Toute autre condition de PokéAPI
      arrête la génération (formes par défaut tolérées, table `pokemon_forms`).
- [x] Bonheur d'évolution : 220 lu dans `GetEvolutionTargetSpecies` des trois dépôts (`pret_gen3_evolution.py`).
      Rouge Feu/Vert Feuille n'ont pas d'horloge : leurs évolutions de jour et de nuit sont en commentaire dans
      pokefirered, donc Évoli n'y devient ni Mentali ni Noctali (à reporter dans `transfer_only.csv` de la branche).
- [x] Méthodes d'apprentissage : `builder_moves.LEARN_METHODS` et `LearnMethod` (Kotlin) ; `light-ball-egg` dans
      l'onglet Œuf avec sa mention, `stadium-surfing-pikachu` (déjà présent en 1re génération et perdu en silence par
      l'application) dans l'onglet Tuteur, mention « Événement externe ». Toute autre méthode arrête la génération
      ou met la fiche en erreur.
- [x] Pokédex : régional (PokéAPI) puis National (`national_dex`) dans `builder.pokedex_links` ; `validate` vérifie
      qu'un Pokémon rencontré figure dans un Pokédex de son jeu et qu'aucun Pokédex ne dépasse la génération du jeu.
      L'application lit encore un seul Pokédex par jeu (`PokedexDao.pokedex`, `min(number)`) : à revoir en phase 6.
- [x] `name_fixes.csv` (nouvelles sortes `method` et `item`, sortes validées) : noms PokéAPI des versions, attaques,
      talents et objets relus ; corrigés : Cherche VS (Rouge Feu/Vert Feuille), cinq méthodes de rencontre, et les
      lieux sans nom nécessaires aux tables (Centres Pokémon des événements, Île Mirage, trois zones de la Grotte
      Tréfonds). Les autres lieux de Hoenn et de Kanto restent à relire dans leur branche.
- [x] `sprites.py` : les espèces 252 à 386 passent par le chemin existant (Noir et Blanc, jusqu'au n° 649) ;
      `form_sprites.py` (ex-`unown_sprites.py`) ajoute Morphéo (soleil, pluie, neige) et Deoxys (Attaque, Défense,
      Vitesse). Icônes d'objets cherchées aussi par identifiant (`data/item-unlinked.json` de pokesprite) : les 33
      objets de la phase 0 sont trouvés, et la Multi Exp et le Bon Commande de l'application ont leur icône.
      Les images 252 à 386 seront téléchargées quand les jeux entreront dans l'aperçu.
- [x] `test_future_generations.py` : Rubis/Saphir construit avec le vrai `RUBY_SAPPHIRE`.
- [x] Tests (`test_gen3_pokemon.py`, `test_form_sprites.py`, `test_sprites.py`) : talents de Hoenn, objets tenus,
      deux Pokédex par jeu, conditions d'évolution et règles du moteur, méthodes classées et refusées, rencontres
      uniques et d'événement, obtention complète des deux Pokédex de Hoenn sur une base réduite.

Branche Hoenn :

- [x] Région `HOENN` (départ `LITTLEROOT_TOWN`), numéro de carte du monde libre (997) : déclarée avec les jeux.
- [x] Obtention vérifiée **par branche** (`validate._check_obtainable`, branche = famille de cartes de
      `games.DECLARED_GAMES`) et non plus par génération : sinon les espèces des Îles Sevii compteraient pour Hoenn.
      Les exclusivités Rubis ↔ Saphir (et Rubis/Saphir ↔ Émeraude) s'obtiennent dans un jeu de la branche : aucune
      ligne. La reproduction donne la plus petite espèce de la famille qui existe dans la génération (Marill pond
      Marill en 2e génération, Azurill en 3e). Un jeu inconnu ou une colonne en trop dans `transfer_only.csv` arrête
      le contrôle.
- [x] `transfer_only.csv` : 138 espèces de Kanto et de Johto absentes de Hoenn, pour Rubis/Saphir et Émeraude ;
      136 s'obtiennent dans Rouge Feu/Vert Feuille (calculé sur les données), Mentali et Noctali par un Évoli échangé
      (ou Pokémon Colosseum), Lugia et Ho-Oh par Colosseum/XD (Roc Nombri, événement).
- [x] `name_fixes.csv` : lieux de Hoenn relus d'après Poképédia. Chenaux 105-109, 122, 124-134 (PokéAPI dit « Route »
      pour les zones), étages et sous-sols sans abréviation, marée haute de la Grotte Tréfonds, extension du Parc
      Safari, Centre Météo, Île Lointaine, Grotte de l'Îlot, zone du Centre Pokémon (Hoenn), objet « Lettre ». Le
      Roc Nombri (et non « Nombril de la Mer ») et la Grotte Métamo gardent le nom de PokéAPI. Toute clé inconnue
      de PokéAPI ou colonne en trop arrête la génération.
- [x] `extra_items.csv` : aucun ajout. Tous les objets de `include/constants/items.h` de pokeruby et pokeemerald
      existent dans PokéAPI (test `test_every_hoenn_item_constant_is_known_to_pokeapi`) ; Clés Salle 1/2/4/6,
      Ticketmystik et Ticketaurora y sont reliés par `pret_identifiers.ITEM_ALIASES`.

Branche Remake 1G :

- [x] Régions Kanto de Rouge Feu (départ `PALLET_TOWN`) et `SEVII` (départ `ONE_ISLAND`), numéros libres (996, 995) :
      déclarées avec les jeux.
- [ ] `transfer_only.csv` : espèces de Hoenn et de Johto absentes de Rouge Feu/Vert Feuille (contrôle par branche,
      comme Hoenn ; les exclusivités Rouge Feu ↔ Vert Feuille n'ont pas de ligne). D'ici là,
      `test_every_pokemon_of_both_hoenn_dexes_can_be_obtained` ne vérifie que la branche Hoenn.
- [ ] `name_fixes.csv` : lieux de Kanto de Rouge Feu et des Îles Sevii. `extra_items.csv` : objets clés.

## Phase 2 — Lecteur pret de la 3e génération

Nouveaux modules, chacun sous 600 lignes et nommés par responsabilité (sur le modèle de `pret_gen2*.py`).
Le format est commun, mais chaque lecteur choisit sa variante par dépôt (tableaux de la phase 0) :

- [ ] `pret_gen3.py` : façade `Gen3PretRepo`, branchée dans `pret_reader.open_pret` et
      `DatabaseBuilder` (équivalent de `gen2_repo`).
- [ ] `pret_gen3_source.py` : lecture bornée et validée du JSON et des initialiseurs C simples
      (`[MOVE_X] = { .effect = …, }`), avec résolution des `#if` / `.ifdef` de version ; toute forme inconnue
      arrête la lecture (même principe que `conditional_lines`).
- [ ] `pret_gen3_maps.py` : en-têtes, layouts, connexions (dont `dive` / `emerge`), warps, événements
      (`object_events` hors clones, `warp_events`, `coord_events`, `bg_events` dont objets cachés),
      `shared_events_map`, drapeaux qui cachent les objets.
- [ ] `pret_gen3_tilesets.py` : tiles 4 bpp indexées, palettes JASC, métatiles à deux couches ; attributs u16
      (Hoenn) ou u32 (Remake 1G) ; palettes primaires 0-5 / secondaires 6-12 (Hoenn), 0-6 / 7-12 (Remake 1G) ;
      tables de tilesets en assembleur (Rubis) ou en C (Émeraude, Rouge Feu).
- [ ] `pret_gen3_moves.py` : effets et probabilités des attaques ; `move_effects.csv` au format `gen3`.
- [ ] Tests unitaires de chaque lecteur sur des extraits des trois dépôts ; tests `pipeline` sur les sources
      épinglées.

## Phase 3 — Cartes

Communs :

- [ ] `maps_render_gen3.py` : rendu des métatiles (couches basse et haute), bordures, première image des
      tuiles animées ; sprites des PNJ (image de face) avec leur palette.
- [ ] Mesurer tuiles, taille des assets, durée de génération et APK ; signaler tout asset de plus de 5 Mio.
- [ ] Relire visuellement les assemblages (comme la passe « 796 positions d'entrées » des générations 1-2).
- [ ] Tests : régions assemblées sans recouvrement, warps cohérents, plans, `GeneratedMapSectionsTest`.

Branche Hoenn :

- [ ] Carte du monde de Hoenn depuis Bourg-en-Vol (49 cartes) ; niveau « Sous l'eau » relié par `dive` /
      `emerge` ; Parc Safari et extérieur de la Zone de Combat ancrés (`map_anchors.csv`).
- [ ] `map_connection_skips.csv`, `map_parents.csv`, `map_anchors.csv` : Zone de Combat atteinte en bateau,
      Atalanopolis atteinte par Plongée, Pacifiville, Île Mirage, îles d'événement.
- [ ] `map_plans.csv` : Mont Chimnée, Grotte Granite, Tour Céleste, `SHOAL_CAVE` (marée haute / marée basse),
      `SEAFLOOR_CAVERN`, `CAVE_OF_ORIGIN` (étages différents entre Rubis et Émeraude), repaires Magma/Aqua,
      Route Victoire de Hoenn, Tour Mirage, Pyramide.
- [ ] `maps.csv` : noms français des cartes de `ruby-sapphire-emerald` (préremplis d'après
      `region_map_section` et PokéAPI, puis relus ; un nom manquant reste bloquant).
- [ ] Différences Rubis/Saphir ↔ Émeraude : cartes propres à un jeu, 113 cartes aux blocs différents.

Branche Remake 1G :

- [ ] Carte du monde de Kanto depuis Bourg Palette (38 cartes) ; région « Îles Sevii » : 7 ensembles placés par
      `map_anchors.csv`, cartes `PROTOTYPE_SEVII_ISLE_*` écartées.
- [ ] `map_plans.csv` : Sylphe SARL, Tour Pokémon, Grotte Azurée, Route Victoire de Kanto, Îles Écume, Mont
      Braise, Ruines Tanoby, Roc Nombri (événement).
- [ ] `maps.csv` : noms français des cartes de `firered-leafgreen` (un nom manquant reste bloquant).

## Phase 4 — Rencontres, terrains et emplacements

Communs :

- [ ] `pret_gen3_wild.py` + `builder_wild_gen3.py` : herbe, eau, Éclate-Roc, pêche (Canne, Super Canne,
      Méga Canne) ; taux par emplacement du moteur ; tables par version (suffixes fixés en phase 0).
- [ ] Conditions de scénario des rencontres (après la Ligue, Pokédex National) : représentées, pas ignorées.
- [ ] `map_areas.csv` : relier aux cartes les zones PokéAPI encore utilisées (dons, fixes, échanges, errants),
      par famille ; `extra_areas.csv` pour les zones absentes.
- [ ] Errants : généraliser `GEN2_ROAMING_AREA` et lire les routes possibles dans `sRoamerLocations`.
- [ ] Éditeur PC (`tools/spot_editor/`) : libellés des nouveaux groupes (`version_choice.py`), terrains, choix
      de région Hoenn / Kanto / Sevii.
- [ ] `validate.py` : probabilités à 100 % par méthode, chaque Pokémon du Pokédex obtenable.
- [ ] Tests : tables lues, probabilités, terrains, comparaison PokéAPI ↔ pret.

Branche Hoenn :

- [ ] Plongée (`water_mons` des cartes `Underwater_*`, méthode PokéAPI `seaweed`).
- [ ] Barpau (six cases de la Route 119, impossibles à placer : note explicite), Grotte Métamo
      (Émeraude), Parc Safari et son extension d'Émeraude (après la Ligue), épidémies de la TV si retenues,
      Pokémon cachés (Kecleon : `devon-scope`, Simularbre : `wailmer-pail`).
- [ ] `TERRA_CAVE` et `MARINE_CAVE` d'Émeraude (Groudon et Kyogre, entrée qui change de route) : lieux
      possibles listés, comme les errants.
- [ ] Errants Latios/Latias (selon la version).
- [ ] `maps_terrain.py` : terrains d'après le **comportement** des cases (hautes herbes, herbes cendrées, sable
      du désert, sol des grottes, eau, algues sous-marines) ; rochers d'Éclate-Roc = objets de carte. Nouveau
      terrain sous-marin : `SpotKind` (Kotlin), `TERRAINS` (Python), validation, éditeur des emplacements.
- [ ] Placer et relire les emplacements de `ruby-sapphire-emerald` dans `map_spots.csv` (colonne `version_group`
      pour les cartes qui diffèrent) ; zéro avertissement de terrain trop petit, ou décision écrite.

Branche Remake 1G :

- [ ] Ruines Tanoby (lettres de Zarbi par salle), Îles Sevii après le Pokédex National, Grotte Métamo (Île 6).
- [ ] Errants Raikou/Entei/Suicune selon le starter.
- [ ] `maps_terrain.py` : terrains d'après le **type de rencontre** de l'attribut (u32), pas le comportement.
- [ ] Placer et relire les emplacements de `firered-leafgreen` dans `map_spots.csv` ; zéro avertissement de
      terrain trop petit, ou décision écrite.

## Phase 5 — Dresseurs, personnages, installations et offres

Communs :

- [ ] `pret_gen3_trainers.py` : équipes, attaques par défaut (calculées comme le moteur), objets tenus,
      combats doubles, toutes les équipes de revanche avec leur condition (table propre à chaque dépôt).
- [ ] `trainer_classes.csv`, `npc_names.csv`, `npc_text_names.csv`, `facility_names.csv` : nouveaux noms
      français (un nom manquant arrête la génération).
- [ ] Objets au sol (Poké Balls de carte) et objets cachés, avec le drapeau qui les retire.
- [ ] `pret_gen3_scripts.py` + `pret_gen3_offers.py` : dons d'objets et de Pokémon, œufs, boutiques (dont les
      listes qui changent avec les badges), échanges, tuteurs, soins, baies offertes.
- [ ] `pret_gen3_conditions.py` : analyse de flot des scripts (`goto_if_set`, `goto_if_eq` sur les `VAR_…`,
      présence des personnages) ; étendre `story_events.csv` aux variables de scénario à valeur.
- [ ] Déblocage du Pokédex National relu dans les scripts de chaque jeu (décision « comme dans les jeux »).
- [ ] `npc_duplicates.csv`, `npc_offers.csv` : personnages présents à plusieurs étapes, offres non lisibles.
- [ ] Tests : offres, conditions, drapeaux et variables relus, dresseurs.

Branche Hoenn :

- [ ] Fossiles ranimés (Devon à Mérouville), Pension (Route 117), Casino de Lavandia, Atelier du Verre (cendres),
      Maître des Capacités et tuteurs d'Émeraude, échanges de la Zone de Combat (PC).
- [ ] Nouvelles monnaies et services dans le domaine et les ressources françaises : Points Combat, cendres
      (`CharacterService`, `OfferKind`, `CharacterRole`, prix affichés).
- [ ] Pokémon fixes : Regis, Groudon, Kyogre, Rayquaza, Électrode, Kecleon, Latios/Latias de l'Île du Sud
      (événement).

Branche Remake 1G :

- [ ] Fossiles ranimés (labo de Cramois'Île), Pension (Île 4), Casino de Céladopole, tuteurs uniques,
      Effaceur, Cherche VS.
- [ ] Pokémon fixes : Ronflex, Électrode, oiseaux légendaires, Mewtwo, Ho-Oh/Lugia/Deoxys (événement).

## Phase 6 — Application : prise en charge générale de la 3e génération

Domaine et données :

- [ ] Choix du jeu : section « 3e génération » puis ligne « Remake 1G » (donnée du jeu, pas un test sur
      l'identifiant) ; jaquettes relues à l'écran.
- [ ] Remplacer les tests `generationId >= 2` par une capacité du jeu : moments de la journée présents ou non
      (dérivé des rencontres ou d'une colonne de `version_group`), calque Baies présent si la carte en a.
- [ ] `MapViewModel` : conserver lieu, filtre et surbrillance selon la famille de cartes, pas selon la génération.
- [ ] `ObtainMethod` : `seaweed` (Plongée), `roaming-water`, `devon-scope`, `wailmer-pail`,
      `feebas-tile-fishing`, méthodes d'événement externe ; filtres de la liste du lieu (`ZoneEncounterFilters`).
- [ ] Capture : `CaptureGeneration.GEN3` (formule à quatre secousses), nouvelles Balls (Filet, Scuba, Faiblo,
      Bis, Chrono, Luxe, Honor) et leur contexte (sous l'eau, tours, déjà capturé) ; contrôles propres à la 3e
      génération à la place de `JohtoBallControls` ; texte `catch_note_gen3`.
- [ ] Pokédex : régional puis National, comme dans les jeux ; bascule entre les deux dans l'écran Pokédex.
- [ ] Zarbi : formes disponibles par jeu (Rouge Feu/Vert Feuille seulement), 28 formes dans le Pokédex.
- [ ] Onglets d'attaques : œuf, tuteur et `light-ball-egg` affichés selon les données du jeu.
- [ ] Talents : section déjà prête (`GenerationFeature.ABILITIES`) à vérifier avec de vraies données.
- [ ] Natures : nouvelle table (`natures` PokéAPI) si la reproduction ou les fiches en ont besoin.
- [ ] Formes retenues (Deoxys selon le jeu, Morphéo) sur la fiche et dans les sprites.
- [ ] Mention « événement externe » sur les cartes, rencontres et offres concernées.
- [ ] Généraliser les plages de versions : `CollectionBackup`, `BackupJson` (386 espèces, 28 formes),
      `CollectionBackupRepository`, `GuideSettings`, en validant contre les jeux de la base plutôt que `1..6`.
      Sauvegarde : rester au schéma 1 (plages élargies) ou passer au schéma 2, avec test d'import d'un ancien
      fichier.
- [ ] Schéma de la base : `SCHEMA_VERSION` (`builder.py`) et version Room alignés, `PokedexSchemaTest` vert.
- [ ] Carte : menu des régions avec Hoenn, Kanto, Îles Sevii ; sélecteur d'étage pour le monde sous-marin et les
      marées ; performances mesurées sur la plus grande carte du monde (règle 3).

Intégration des jeux :

- [ ] Branche Hoenn : passer **Émeraude** de `GAMES_IN_PROGRESS` à `GAMES` (régénération explicite,
      `assets.sha256`).
- [ ] Puis **Rubis/Saphir** : variantes de format de pokeruby, différences de cartes et de scénario.
- [ ] Branche Remake 1G : **Rouge Feu/Vert Feuille**.
- [ ] Tests JVM : chaque ViewModel modifié teste vide et erreur ; `PokemapsJourneyTest` couvre un jeu de chaque
      branche ; `MapViewModelTest` couvre le passage Émeraude → Rouge Feu ; tests de capture GEN3.
- [ ] Essai sur appareil ou émulateur (mémoire `emulator-for-device-checks`) : carte de Hoenn, Plongée, Îles
      Sevii, Pokédex régional et National, fiche, capture ; installation `-r` sans perte des collections.

## Phase 7 — Guides, succès et outils

Communs :

- [ ] Textes dans des fichiers de ressources séparés (`strings.xml` dépasse 3 600 lignes) ; balises
      `[[pokemon:…]]`, `[[place:…]]` validées par `GuideRepositoryTest` (qui charge alors 11 bibliothèques).
- [ ] Sources éditoriales dans `GuideDefinition.kt` : remplacer `KANTO_VERSIONS`/`JOHTO_VERSIONS` par des
      ensembles nommés par jeu.
- [ ] Succès RetroAchievements des cinq jeux : instantané traduit, identifiants officiels relevés sur le site
      (ne pas les deviner), `RetroGames.ids`, `CaptureGoals`, `unownGoal` et objectif de 28 formes.
- [ ] Errants : `Roamers` par jeu (routes, espèces, dépendance à la version ou au starter) et réglages.
- [ ] Reproduction de la 3e génération : IV au lieu des DV, talents, CT du père ; `BreedingUseCase` ne doit plus
      exiger la génération 2.
- [ ] Bonheur de la 3e génération : barème propre, à la place du paramètre `versionId == 6`.

Branche Hoenn :

- [ ] Soluces originales de Hoenn (avec les différences d'Émeraude), quêtes annexes, astuces, bugs et glitches.
- [ ] Événements quotidiens (Île Mirage, marées, loterie, Maison Piège) à la place des événements
      hebdomadaires de Johto.
- [ ] `CaptureGoals` : Pokédex de Hoenn, choix exclusifs (starter, fossiles Lilia/Anorith, Kecleon…).
- [ ] Pierre Stase (Émeraude) dans la reproduction.

Branche Remake 1G :

- [ ] Soluces originales de Kanto de Rouge Feu/Vert Feuille et des Îles Sevii, quêtes annexes, astuces, bugs.
- [ ] `CaptureGoals` : Pokédex de Kanto puis National, choix exclusifs (starter, fossiles, Kicklee/Tygnon…).

## Phase 8 — Contenus propres à Hoenn : baies, concours, Pokéblocs, décorations

- [ ] Arbres à baies (sol meuble et baie initiale lus dans `setberrytree` de `new_game.inc`) : calque « Baies »
      et `OfferKind.FRUIT_TREE`, données des baies (`src/berry.c`, PokéAPI `berries`, `berry_flavors`).
- [ ] Concours : salles et rangs, catégories et effets de concours des attaques (`src/data/contest_moves.h`,
      PokéAPI `contest_effects`, `contest_combos`), affichés sur la fiche d'attaque.
- [ ] Pokéblocs : recettes et saveurs selon les baies, Mélangeur, Boîte Pokéblocs, usage au Parc Safari.
- [ ] Décorations des Bases Secrètes : nouvelle entité (`src/data/decoration/`), noms français relus dans un CSV,
      où les obtenir (Cimetronelle, Centre Commercial de Nénucrique, dons, lots).
- [ ] Tests du pipeline et JVM de chacune de ces données ; `RELEASE_NOTES.md`.

## Phase 9 — Documentation, publication et bilan

- [ ] `README.md` : présentation (onze jeux, deux branches), sources pret de la 3e génération, « Ajouter un jeu »
      (format GEN3), éditeur des emplacements, mesures de génération et d'APK, procédure inchangée.
- [ ] `docs/generations/generation-3.md` (nouveau), `generations-suivantes.md`, nouveau bilan avant la
      génération 4, `docs/fonctionnalites/*.md`, `docs/donnees/pipeline.md` (déjà en retard sur le README :
      il dit encore que les données ne sont pas versionnées), `docs/developpement.md`.
- [ ] `docs/donnees/sprites-pokemon.md` régénéré (`tools/build_sprite_catalog.py`) : 1 à 386 embarqués.
- [ ] `AGENTS.md` §1 (liste des jeux) ; `about_credit_pret` (tous les dépôts pret utilisés).
- [ ] Captures d'écran du README (Hoenn, Îles Sevii), sur l'émulateur Android 17.
- [ ] `RELEASE_NOTES.md` : une phrase française par changement visible, sous `<!-- notes -->`.
- [ ] CI : durée de la génération, taille du cache et de l'APK dans le résumé ; workflow `data-pipeline.yml`.
- [ ] Relecture visuelle finale des cartes, des emplacements et des offres ; bilan écrit des limites connues.

---

## Contrôle final : ce qui pourrait être oublié

Liste relue à la fin, une fois toutes les phases cochées :

- [ ] Plus aucun `generationId >= 2`, `== 2`, `1..6`, `4..6`, `251`, `26` restant sans justification
      (`grep` sur `app/src/main/java`).
- [ ] Aucune méthode de rencontre, méthode d'apprentissage, classe de dresseur, drapeau ou variable de scénario
      ignoré en silence : chaque inconnu arrête la génération ou le chargement.
- [ ] Aucun fait d'une branche supposé vrai pour l'autre : Pokédex, régions, terrains, offres et guides relus
      séparément pour Hoenn et pour le Remake 1G.
- [ ] Bascule entre deux jeux de la même génération mais de régions différentes testée (lieu, surbrillance).
- [ ] Le filtre et le voile horaires n'apparaissent pas en 3e génération ; ils restent en 2e.
- [ ] Le calculateur de capture apparaît en 3e génération avec les bonnes Balls.
- [ ] Pokédex régional puis National, comme dans chaque jeu.
- [ ] Sauvegarde de collection : export/import avec les versions 7 à 11, 386 espèces et 28 formes ; import
      d'un ancien fichier de schéma 1.
- [ ] RetroAchievements : synchronisation des cinq nouveaux jeux, une requête par jeu, aucune au lancement.
- [ ] Recherche, fiches objet/attaque/lieu/personnage, liens carte ↔ Pokédex pour les nouveaux jeux.
- [ ] Sprites : espèces 252-386, chromatiques, formes, icônes d'objets, PNJ ; aucun chemin d'image cassé
      (`python tools/check_assets.py`).
- [ ] Fichiers sous 600 lignes et fonctions sous 60 lignes, Python comme Kotlin, tests compris.
- [ ] `assets.sha256` à jour, aucun cache ni aperçu versionné, aucun asset disproportionné, tailles rapportées.
- [ ] Aucun service Google Play (`checkNoGoogleServices`), interface entièrement en français.
- [ ] Documentation et `AGENTS.md` cohérents avec le comportement réel.
- [ ] Contrôles de `AGENTS.md` §8 tous verts, y compris `pytest -m pipeline` après génération.

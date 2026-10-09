# Plan — Génération 3 (Rubis, Saphir, Émeraude, Rouge Feu, Vert Feuille)

Plan de travail pour ajouter la 3e génération à Pokémaps, construit sur ce qui a été fait pour les
générations 1 et 2 (commits « Gen 2 (phases 0 à 3) » → « phase 8 », `docs/generations/bilan-generations-1-2.md`).
Chaque phase se termine par les contrôles de `AGENTS.md` §8, sans avertissement, et ne laisse aucun `TODO`.
Les cases se cochent au fil de l'eau ; une décision prise se note dans la section « Décisions ».

Rappel du principe hérité de la génération 2 : un jeu entre d'abord dans `GAMES_IN_PROGRESS`
(`tools/pokemaps_data/games.py`), il est généré et validé dans l'aperçu `tools/build/preview/`, puis il passe
dans `GAMES` seulement quand l'application sait tout afficher.

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
  Kanto (151). Les espèces de Johto des Îles Sevii et du Parc Safari d'Émeraude n'y sont **pas**.
- Tables déjà prêtes (vides jusqu'ici) : talents (`pokemon_ability`, `ability_version_group`), objets tenus
  via PokéAPI à partir de la 3e génération (`builder_items._pokeapi_held_items`), `test_future_generations.py`.
- Sprites Noir/Blanc disponibles jusqu'au n° 649 : les n° 252 à 386 sont couverts. Les 28 formes de Zarbi
  (dont ! et ?) sont déjà embarquées (`sprites/unown`, 112 fichiers).
- Classes de dégâts par type jusqu'à la 3e génération : déjà gérées (`builder_moves._damage_class`).

### Valeurs codées en dur pour les générations 1-2 (à généraliser)

| Endroit | Hypothèse actuelle |
|---|---|
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
| `tools/spot_editor/version_choice.py` | `_VERSION_LABELS` des quatre groupes actuels |
| `tools/pokemaps_data/sources.py` | `git fetch` borné à 120 s (dépôts GBA plus lourds) |
| `res/values/strings.xml` `about_credit_pret` | cite seulement pokered et pokeyellow (déjà incomplet) |
| `AGENTS.md` §1, `README.md`, `docs/` | listent les six jeux actuels |

---

## Décisions à prendre (phase 0)

- [ ] **Ordre d'intégration.** Recommandé : Émeraude d'abord (pret/pokeemerald est le désassemblage le plus
      abouti), puis Rubis/Saphir comme variante de la même famille (comme Cristal après Or/Argent), puis Rouge
      Feu/Vert Feuille (pret/pokefirered, famille distincte de Rouge/Bleu/Jaune).
- [ ] **Familles de cartes** : `ruby-sapphire-emerald` et `firered-leafgreen` (plans différents de la 1re
      génération : aucun partage de `map_spots.csv` avec `red-blue-yellow`).
- [ ] **Source des rencontres aléatoires** : recommandé `wild_encounters.json` de pret (comme la génération 2,
      lu comme le moteur, relié directement aux constantes de carte), PokéAPI gardant dons, fixes, échanges et
      errants. Un test compare les deux sources pour signaler les écarts.
- [ ] **Pokédex affiché** : régional seul, ou régional + national (indispensable pour les espèces de Johto des
      Îles Sevii et du Parc Safari d'Émeraude). Recommandé : national limité à 386, ordre régional conservé.
- [ ] **Îles Sevii** : une région « Îles Sevii » unique dont les îles non reliées sont placées par
      `map_anchors.csv` (comme la carte de la ville), ou une région par groupe d'îles.
- [ ] **Monde sous-marin (Plongée)** : niveau distinct de la carte du monde de Hoenn (sélecteur d'étage) ou
      carte à part ancrée sur les routes 124 à 128.
- [ ] **`SHOAL_CAVE` et ses marées** (cartes marée haute / marée basse) : présentées comme deux niveaux.
- [ ] **Contenus d'événement** (Île Lointaine, Île Aurore, Nombril de la Mer, Billet Éon, e-Reader, Mystery
      Gift, Pokémon Box, Colosseum) : exclus, ou affichés avec la mention « événement externe ».
- [ ] **Zone de Combat / Pyramide / Butte d'Entraînement (Émeraude)** : cartes affichées, contenu aléatoire
      non simulé ; dire explicitement ce qui n'est pas listé.
- [ ] **Décorations des Bases Secrètes** : absentes de PokéAPI. Exclues, ou nouvelle entité (coût élevé).
- [ ] **Revanches** (PokéNav, Match Call, Cherche VS) : afficher toutes les équipes du dresseur ou seulement la
      première.
- [ ] **Formes** : Morphéo (4 formes météo), Deoxys (forme différente selon le jeu : Normale R/S, Attaque RF,
      Défense VF, Vitesse E), Spinda. Recommandé : forme du jeu pour Deoxys, formes listées pour Morphéo.
- [ ] **Concours, Pokéblocs, Baies** (Hoenn) : dans le périmètre de cette intégration ou en complément après.
- [ ] **Budget de taille** : APK actuel 59,85 Mio, assets versionnés sans LFS. Fixer une limite acceptable
      pour l'APK et pour la croissance du dépôt Git (chaque régénération des tuiles s'ajoute à l'historique).
- [ ] **Jaquettes** : Groudon (Rubis), Kyogre (Saphir), Rayquaza (Émeraude), Dracaufeu (Rouge Feu),
      Florizarre (Vert Feuille) et leurs couleurs.

---

## Phase 0 — Reconnaissance des sources et cadrage

- [ ] Choisir et épingler les commits de `pret/pokeruby`, `pret/pokeemerald`, `pret/pokefirered` dans
      `PRET_COMMITS` (`sources.py`) ; vérifier la licence et l'absence de ROM nécessaire pour lire les données.
- [ ] Mesurer la taille d'un `git fetch --depth 1` de chaque dépôt ; adapter le délai de `fetch_pret`
      (120 s) avec une borne explicite, et la clé de cache CI (`.github/actions/build-database/action.yml`,
      `data-pipeline.yml`).
- [ ] Recenser dans chaque dépôt, et noter dans ce plan, les fichiers à lire et leurs variantes :
  - [ ] cartes : `data/maps/<Carte>/map.json`, `data/maps/map_groups.json`, `data/layouts/layouts.json`,
        `map.bin`, `border.bin` ;
  - [ ] tilesets : `data/tilesets/{primary,secondary}/<nom>/tiles.png`, `palettes/*.pal`, `metatiles.bin`,
        `metatile_attributes.bin`, tables de tilesets (`src/data/tilesets/headers.h`) ;
  - [ ] comportements de cases : `include/constants/metatile_behaviors.h`, `src/metatile_behavior.c`
        (`MetatileBehavior_IsLandWildEncounter`, `…IsWaterWildEncounter`, Plongée) ;
  - [ ] rencontres : `src/data/wild_encounters.json` (ou son équivalent dans pokeruby) ;
  - [ ] dresseurs : `src/data/trainers.h`, `src/data/trainer_parties.h`, classes et revanches ;
  - [ ] attaques : `src/data/battle_moves.h` (effet, probabilité), `data/battle_scripts_1.s` ;
  - [ ] objets, Pokémon de base (objets tenus), échanges (`src/data/trade.h`), tuteurs, errants
        (`src/roamer.c`), baies (`src/berry.c`), scripts (`data/maps/*/scripts.inc`, `data/scripts/*.inc`) ;
  - [ ] sprites des PNJ : `graphics/object_events/pics/**` et leurs palettes.
- [ ] Identifier comment chaque dépôt distingue ses versions (`#if` de compilation pour Rubis/Saphir,
      Rouge Feu/Vert Feuille, suffixes des tables de rencontres) ; fixer les symboles de `pret_versions`.
- [ ] Vérifier les icônes pokesprite des objets de la 3e génération (baies, Balls, objets clés) et lister
      les manquants.
- [ ] Prendre les décisions de la section précédente et mettre à jour ce plan.

## Phase 1 — Données Pokémon (PokéAPI) dans l'aperçu

- [ ] `games.py` : ajouter `PretFormat.GEN3`, les régions `HOENN` (départ `LITTLEROOT_TOWN`),
      Kanto de Rouge Feu (départ `PALLET_TOWN`) et `SEVII`, avec des numéros de carte du monde libres
      (997, 996…), et les jeux dans `GAMES_IN_PROGRESS` avec leurs `VersionCover`.
- [ ] `ONE_OFF_METHODS` : ajouter `roaming-water`, `devon-scope`, `wailmer-pail` ; statuer sur
      `feebas-tile-fishing` (aléatoire sur six cases).
- [ ] Méthodes d'événement externe (`colosseum-bonus-disc-*`, `pokemon-channel-pal`) : écartées à la génération
      avec une raison écrite (`encounter_curation.csv` ou règle explicite), jamais perdues en silence.
- [ ] Espèces 252 à 386 : stats, types, talents (talent caché absent en 3e génération), objets tenus,
      groupes d'œufs, évolutions (nouveaux déclencheurs : Ningale/Munja, Barpau par Beauté, Chenipotte selon la
      personnalité) ; vérifier que `evolution` sait les représenter, sinon étendre le schéma.
- [ ] Bonheur d'évolution de la 3e génération : vérifier le seuil réel (220) contre pret, comme
      `_happiness_to_evolve` le fait pour la 2e génération.
- [ ] Méthodes d'apprentissage : classer `light-ball-egg` et refuser toute méthode inconnue (côté Python et
      Kotlin) au lieu de la perdre.
- [ ] Pokédex : appliquer la décision régional/national dans `builder.py` et `validate._check_obtainable`.
- [ ] `transfer_only.csv` : exclusivités de version et espèces obtenues seulement par échange (Rubis ↔ Saphir,
      Rouge Feu ↔ Vert Feuille, Johto, Colosseum/XD).
- [ ] `name_fixes.csv` : relire les noms français des nouveaux objets, attaques, talents et lieux, et des
      versions (Rubis, Saphir, Émeraude, Rouge Feu, Vert Feuille) affichés sous les jaquettes.
- [ ] `extra_items.csv` : objets clés ou objets de scénario absents de PokéAPI (à recenser en phase 0).
- [ ] `sprites.py` : générer les sprites 252 à 386 (normal, chromatique, animé, fixe) ; formes retenues
      (Deoxys, Morphéo) ; icônes d'objets manquantes.
- [ ] Mettre à jour `test_future_generations.py` (il construit `ruby-sapphire` avec un faux `PretFormat.GEN1`).
- [ ] Tests : talents d'une espèce de Hoenn, objets tenus, Pokédex, méthodes classées, obtention complète.

## Phase 2 — Lecteur pret de la 3e génération

Nouveaux modules, chacun sous 600 lignes et nommés par responsabilité (sur le modèle de `pret_gen2*.py`) :

- [ ] `pret_gen3.py` : façade `Gen3PretRepo`, branchée dans `pret_reader.open_pret` et
      `DatabaseBuilder` (équivalent de `gen2_repo`).
- [ ] `pret_gen3_source.py` : lecture bornée et validée du JSON et des initialiseurs C simples
      (`[MOVE_X] = { .effect = …, }`), avec résolution des `#if` de version ; toute forme inconnue arrête la
      lecture (même principe que `conditional_lines`).
- [ ] `pret_gen3_maps.py` : en-têtes, layouts, connexions, warps, événements (`object_events`,
      `warp_events`, `coord_events`, `bg_events` dont objets cachés), drapeaux qui cachent les objets.
- [ ] `pret_gen3_tilesets.py` : tiles 4 bpp indexées, palettes JASC, métatiles à deux couches,
      attributs de comportement ; palettes primaires 0-5 et secondaires 6-12.
- [ ] `pret_gen3_moves.py` : effets et probabilités des attaques ; `move_effects.csv` au format `gen3`.
- [ ] Tests unitaires de chaque lecteur sur des extraits ; tests `pipeline` sur les sources épinglées.

## Phase 3 — Cartes de Hoenn, de Kanto (Rouge Feu/Vert Feuille) et des Îles Sevii

- [ ] `maps_render_gen3.py` : rendu des métatiles (couches basse et haute), bordures, première image des
      tuiles animées ; sprites des PNJ (image de face) avec leur palette.
- [ ] Assemblage des cartes du monde par connexions (`maps_layout.py`) : Hoenn entier depuis Bourg-en-Vol ;
      Kanto depuis Bourg Palette ; Îles Sevii selon la décision (ancres dans `map_anchors.csv`).
- [ ] `map_connection_skips.csv`, `map_parents.csv`, `map_anchors.csv` : cas propres à Hoenn (Zone de Combat
      atteinte en bateau, Atalanopolis atteinte par Plongée, Pacifiville, Île Mirage).
- [ ] Plans d'étages et zones d'un même niveau (`map_plans.csv`) : Mont Chimnée, Grotte Granite, Tour
      Céleste, `SHOAL_CAVE` (marées), `SEAFLOOR_CAVERN`, `CAVE_OF_ORIGIN`, repaires Magma/Aqua, Sylphe SARL,
      Tour Pokémon,
      Grotte Azurée, Route Victoire des deux régions, Ruines Tanoby, monde sous-marin.
- [ ] `maps.csv` : noms français de toutes les cartes des deux familles (préremplir d'après
      `region_map_section` et les noms PokéAPI, puis relire ; un nom manquant reste bloquant).
- [ ] Mesurer tuiles, taille des assets, durée de génération et APK ; comparer au budget de la phase 0.
- [ ] Relire visuellement les assemblages (comme la passe « 796 positions d'entrées » des générations 1-2).
- [ ] Tests : régions assemblées sans recouvrement, warps cohérents, plans, `GeneratedMapSectionsTest`.

## Phase 4 — Rencontres, terrains et emplacements

- [ ] `pret_gen3_wild.py` + `builder_wild_gen3.py` : herbe, eau, Éclate-Roc, pêche (Canne, Super Canne,
      Méga Canne), Plongée ; taux par emplacement du moteur ; variantes de version.
- [ ] Cas particuliers : Barpau (six cases de la Route 119, impossibles à placer : note explicite),
      Grotte Altération (Émeraude), Parc Safari de Hoenn et son extension d'Émeraude (après la Ligue),
      Ruines Tanoby (lettres de Zarbi par salle), Îles Sevii après le Pokédex National, épidémies de la TV si
      retenues, Pokémon cachés (Kecleon : `devon-scope`, Simularbre : `wailmer-pail`).
- [ ] `TERRA_CAVE` et `MARINE_CAVE` d'Émeraude (Groudon et Kyogre, entrée qui change de route) : lieux
      possibles listés, comme les errants.
- [ ] Conditions de scénario des rencontres (après la Ligue, Pokédex National) : représentées, pas ignorées.
- [ ] `map_areas.csv` : relier aux cartes les zones PokéAPI encore utilisées (dons, fixes, échanges, errants),
      par famille ; `extra_areas.csv` pour les zones absentes.
- [ ] Errants : Latios/Latias (Hoenn), Raikou/Entei/Suicune selon le starter (Rouge Feu/Vert Feuille) ;
      généraliser `GEN2_ROAMING_AREA` et lire les routes possibles dans pret.
- [ ] `maps_terrain.py` : terrains d'après les comportements du moteur (hautes herbes, herbes cendrées,
      sable du désert, sol des grottes, eau, algues sous-marines) ; rochers d'Éclate-Roc = objets de carte.
- [ ] Nouveau terrain sous-marin si retenu : `SpotKind` (Kotlin), `TERRAINS` (Python), validation,
      éditeur des emplacements.
- [ ] Éditeur PC (`tools/spot_editor/`) : libellés des nouveaux groupes (`version_choice.py`), terrains,
      choix de région Hoenn / Kanto / Sevii.
- [ ] Placer et relire les emplacements dans `map_spots.csv` pour les deux familles ; zéro avertissement de
      terrain trop petit, ou décision écrite.
- [ ] `validate.py` : probabilités à 100 % par méthode, chaque Pokémon du Pokédex obtenable.
- [ ] Tests : tables lues, probabilités, terrains, comparaison PokéAPI ↔ pret.

## Phase 5 — Dresseurs, personnages, installations et offres

- [ ] `pret_gen3_trainers.py` : équipes, attaques par défaut (calculées comme le moteur), objets tenus,
      combats doubles, revanches (selon la décision).
- [ ] `trainer_classes.csv`, `npc_names.csv`, `npc_text_names.csv`, `facility_names.csv` : nouveaux noms
      français (un nom manquant arrête la génération).
- [ ] Objets au sol (Poké Balls de carte) et objets cachés, avec le drapeau qui les retire.
- [ ] `pret_gen3_scripts.py` + `pret_gen3_offers.py` : dons d'objets et de Pokémon, œufs, fossiles ranimés
      (Devon à Mérouville, labo de Cramois'Île), boutiques
      (dont les listes qui changent avec les badges), échanges (`trade.h`), tuteurs (Émeraude, Rouge Feu/Vert
      Feuille, tuteurs uniques), Maître des Capacités, Effaceur, Pension (Route 117, Île 4), soins, Casino de
      Lavandia et de Céladopole, Atelier du Verre (cendres), échanges de la Zone de Combat (PC), baies offertes.
- [ ] Nouvelles monnaies ou nouveaux services dans le domaine et les ressources françaises : Points Combat,
      cendres, Maître des Capacités (`CharacterService`, `OfferKind`, `CharacterRole`, prix affichés).
- [ ] Arbres à baies d'Hoenn (sol meuble et baie initiale) : calque « Baies » et `OfferKind.FRUIT_TREE`.
- [ ] `pret_gen3_conditions.py` : analyse de flot des scripts (`goto_if_set`, `goto_if_eq` sur les `VAR_…`,
      présence des personnages) ; étendre `story_events.csv` aux variables de scénario à valeur.
- [ ] `npc_duplicates.csv`, `npc_offers.csv` : personnages présents à plusieurs étapes, offres non lisibles.
- [ ] Pokémon fixes (Regis, Groudon, Kyogre, Rayquaza, Électrode, Ronflex, oiseaux légendaires, Mewtwo).
- [ ] Tests : offres, conditions, drapeaux et variables relus, dresseurs.

## Phase 6 — Application : prise en charge générale de la 3e génération

Domaine et données :

- [ ] Remplacer les tests `generationId >= 2` par une capacité du jeu : moments de la journée présents ou non
      (dérivé des rencontres ou d'une colonne de `version_group`), calque Baies présent si la carte en a.
- [ ] `MapViewModel` : conserver lieu, filtre et surbrillance selon la famille de cartes, pas selon la génération.
- [ ] `ObtainMethod` : `seaweed` (nouvelle méthode Plongée ou rattachement décidé), `roaming-water`,
      `devon-scope`, `wailmer-pail`, `feebas-tile-fishing` ; filtres de la liste du lieu (`ZoneEncounterFilters`).
- [ ] Capture : `CaptureGeneration.GEN3` (formule à quatre secousses), nouvelles Balls (Filet, Scuba, Faiblo,
      Bis, Chrono, Luxe, Honor) et leur contexte (sous l'eau, tours, déjà capturé) ; contrôles propres à
      Hoenn à la place de `JohtoBallControls` ; texte `catch_note_gen3`.
- [ ] Zarbi : formes disponibles par jeu (Rouge Feu/Vert Feuille seulement), 28 formes dans le Pokédex.
- [ ] Onglets d'attaques : œuf, tuteur et `light-ball-egg` affichés selon les données du jeu.
- [ ] Talents : section déjà prête (`GenerationFeature.ABILITIES`) à vérifier avec de vraies données.
- [ ] Natures : nouvelle table (`natures` PokéAPI) si la reproduction ou les fiches en ont besoin.
- [ ] Formes retenues (Deoxys selon le jeu, Morphéo) sur la fiche et dans les sprites.
- [ ] Généraliser les plages de versions : `CollectionBackup`, `BackupJson` (386 espèces, 28 formes),
      `CollectionBackupRepository`, `GuideSettings`, en validant contre les jeux de la base plutôt que `1..6`.
      Sauvegarde : rester au schéma 1 (plages élargies) ou passer au schéma 2, avec test d'import d'un ancien
      fichier.
- [ ] Schéma de la base : `SCHEMA_VERSION` (`builder.py`) et version Room alignés, `PokedexSchemaTest` vert.
- [ ] Carte : menu des régions avec Hoenn, Kanto, Îles Sevii ; sélecteur d'étage pour le sous-marin ou les
      marées si retenu ; performances mesurées sur la plus grande carte du monde (règle 3).

Intégration des jeux :

- [ ] Passer **Émeraude** de `GAMES_IN_PROGRESS` à `GAMES` (régénération explicite, `assets.sha256`).
- [ ] Puis **Rubis/Saphir** : variantes de format de pokeruby, différences de cartes et de scénario.
- [ ] Puis **Rouge Feu/Vert Feuille**.
- [ ] Tests JVM : chaque ViewModel modifié teste vide et erreur ; `PokemapsJourneyTest` couvre un jeu de
      Hoenn ; `MapViewModelTest` couvre le passage Émeraude → Rouge Feu ; tests de capture GEN3.
- [ ] Essai sur appareil ou émulateur (mémoire `emulator-for-device-checks`) : carte de Hoenn, Plongée,
      Pokédex, fiche, capture ; installation `-r` sans perte des collections existantes.

## Phase 7 — Guides, succès et outils

- [ ] Soluces originales Hoenn (avec différences d'Émeraude) et Kanto de Rouge Feu/Vert Feuille + Îles Sevii ;
      quêtes annexes, astuces, bugs et glitches ; sources éditoriales dans `GuideDefinition.kt`
      (remplacer `KANTO_VERSIONS`/`JOHTO_VERSIONS` par des ensembles nommés par jeu).
- [ ] Textes dans des fichiers de ressources séparés (`strings.xml` dépasse 3 600 lignes) ; balises
      `[[pokemon:…]]`, `[[place:…]]` validées par `GuideRepositoryTest` (qui charge alors 11 bibliothèques).
- [ ] Événements quotidiens (Île Mirage, marées, loterie, Maison Piège) à la place des événements
      hebdomadaires de Johto.
- [ ] Succès RetroAchievements des cinq jeux : instantané traduit, identifiants officiels relevés sur le
      site (ne pas les deviner), `RetroGames.ids`, `CaptureGoals` (Pokédex de Hoenn, choix exclusifs : starter,
      fossiles Lilia/Anorith, Kecleon…), `unownGoal` et objectif de 28 formes.
- [ ] Errants : `Roamers` par jeu (routes, espèces, dépendance au starter) et réglages correspondants.
- [ ] Reproduction de la 3e génération : IV au lieu des DV, Pierre Stase (Émeraude), talents, CT du père ;
      `BreedingUseCase` ne doit plus exiger la génération 2.
- [ ] Bonheur de la 3e génération : barème propre, à la place du paramètre `versionId == 6`.
- [ ] Concours, Pokéblocs et baies si la décision les retient.

## Phase 8 — Documentation, publication et bilan

- [ ] `README.md` : présentation (onze jeux), sources pret de la 3e génération, « Ajouter un jeu » (format
      GEN3), éditeur des emplacements, mesures de génération et d'APK, procédure inchangée.
- [ ] `docs/generations/generation-3.md` (nouveau), `generations-suivantes.md`, nouveau bilan avant la
      génération 4, `docs/fonctionnalites/*.md`, `docs/donnees/pipeline.md` (déjà en retard sur le README :
      il dit encore que les données ne sont pas versionnées), `docs/developpement.md`.
- [ ] `docs/donnees/sprites-pokemon.md` régénéré (`tools/build_sprite_catalog.py`) : 1 à 386 embarqués.
- [ ] `AGENTS.md` §1 (liste des jeux) ; `about_credit_pret` (tous les dépôts pret utilisés).
- [ ] Captures d'écran du README (Hoenn), sur l'émulateur Android 17.
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
- [ ] Bascule entre deux jeux de la même génération mais de régions différentes testée (lieu, surbrillance).
- [ ] Le filtre et le voile horaires n'apparaissent pas en 3e génération ; ils restent en 2e.
- [ ] Le calculateur de capture apparaît en 3e génération avec les bonnes Balls.
- [ ] Sauvegarde de collection : export/import avec les versions 7 à 11, 386 espèces et 28 formes ; import
      d'un ancien fichier de schéma 1.
- [ ] RetroAchievements : synchronisation des cinq nouveaux jeux, une requête par jeu, aucune au lancement.
- [ ] Recherche, fiches objet/attaque/lieu/personnage, liens carte ↔ Pokédex pour les nouveaux jeux.
- [ ] Sprites : espèces 252-386, chromatiques, formes, icônes d'objets, PNJ ; aucun chemin d'image cassé
      (`python tools/check_assets.py`).
- [ ] Fichiers sous 600 lignes et fonctions sous 60 lignes, Python comme Kotlin, tests compris.
- [ ] `assets.sha256` à jour, aucun cache ni aperçu versionné, taille du dépôt et de l'APK dans le budget.
- [ ] Aucun service Google Play (`checkNoGoogleServices`), interface entièrement en français.
- [ ] Documentation et `AGENTS.md` cohérents avec le comportement réel.
- [ ] Contrôles de `AGENTS.md` §8 tous verts, y compris `pytest -m pipeline` après génération.

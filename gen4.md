# Plan — Génération 4 (Diamant, Perle, Platine)

Plan de travail pour ajouter **Pokémon Diamant, Perle et Platine** à Pokémaps. Il reprend la démarche
des générations 1 à 3 (ancien `docs/plan_gen_3.md`, retiré au commit `586920c7` et lisible avec
`git show 586920c7^:docs/plan_gen_3.md`), corrigée par les exigences actuelles d'`AGENTS.md` et
par les audits d'omissions des 14 et 15 octobre 2026.

**Hors périmètre de ce plan** : Or HeartGold et Argent SoulSilver. Ils formeront une branche distincte,
traitée plus tard, comme le Remake 1G l'a été pour Hoenn. Ne rien préparer pour eux dans cette intégration
au-delà de ce qu'exige un modèle propre (aucun `heartgold-soulsilver` dans `games.py`, aucun cas
« au cas où »).

Règles de conduite :

- Chaque phase se termine par les contrôles d'`AGENTS.md` §8, sans avertissement, sans `TODO`, et par
  le rapport du §12. Les cases se cochent au fil de l'eau. Une décision prise se note dans « Décisions ».
- Les résultats et mesures d'une phase s'écrivent **dans ce plan**, sous la phase. Les pages de `docs/`
  décrivent seulement l'état actuel : aucun rapport de tâche n'y est recopié (`docs/README.md`).
- Un jeu entre d'abord dans `GAMES_IN_PROGRESS` (`tools/pokemaps_data/games.py`). Il est généré et validé
  dans l'aperçu `tools/build/preview/`, puis il passe dans `GAMES` quand l'application sait tout afficher.
- Ne jamais supposer qu'un fait de Platine vaut pour Diamant/Perle, ni l'inverse : chaque fait se lit dans
  la source du jeu concerné, ou il est déclaré commun **par un test** qui compare les deux sources.
- Aucune ROM, aucun prélèvement sur pokemaps.net. Les noms français viennent de PokéAPI et des CSV relus
  (relecture d'après Poképédia, comme pour Hoenn).

---

## Une branche Sinnoh, deux sources de format différent

Diamant, Perle et Platine forment **une seule branche** (une famille de cartes, comme Rubis/Saphir/Émeraude),
mais leurs désassemblages n'ont pas du tout la même forme.

| | Diamant / Perle | Platine |
|---|---|---|
| Groupe PokéAPI | `diamond-pearl` | `platinum` |
| Versions PokéAPI | `diamond`, `pearl` | `platinum` |
| Désassemblage pret | `pret/pokediamond` | `pret/pokeplatinum` |
| Forme des données | surtout des fichiers NARC extraits en binaire (`files/**/narc_NNNN.bin`), quelques JSON | ressources lisibles : JSON, scripts assembleur `.s`, PNG, plus les modèles 3D Nitro |
| Construction de la ROM | exige le compilateur MWCC et le Nitro SDK propriétaires | outils libres (meson) |
| Famille de cartes | `diamond-pearl-platinum` (à confirmer en phase 0) | idem |
| Pokédex | Sinnoh (151 attendu), puis National (493) | Sinnoh étendu (210 attendu), puis National (493) |
| Propre au jeu | Tour de Combat, Clé Secrète (Motisma) | Monde Distorsion, Zone de Combat, Villa, formes de Motisma, Giratina Originel, Shaymin Céleste |

Communs à la branche : moteur Nintendo DS, cartes en **3D** (modèles Nitro `NSBMD`/`NSBTX`), matin/jour/nuit,
séparation physique/spéciale **par attaque**, Souterrain, Super Concours, Poffins, sol meuble et paillis,
arbres à Miel, Grand Marais, Pokéradar, double insertion GBA, Parc des Amis, Cherche VS.

**Choix du jeu** : section « 4e génération » avec Diamant, Perle, Platine sur une ligne, comme les autres
générations (`Game.remakeGenerationId` reste nul).

---

## État de départ (constaté le 15 octobre 2026)

### Application et pipeline

- Onze jeux distribués, `GAMES_IN_PROGRESS` vide. `Generation` (Kotlin) s'arrête à `GEN3(3, 386)` ;
  `GameVersion` s'arrête à `LEAFGREEN(11)` ; `VersionGroup` à `FIRERED_LEAFGREEN`. Un identifiant inconnu
  lève une exception explicite (`Generation.of`, `GameVersion.of`, `VersionGroup.of`).
- `when` exhaustifs sur `Generation` sans `else` (règle 1) : ajouter `GEN4` fera échouer la compilation
  à chaque endroit qui doit décider. C'est voulu : chaque erreur est une décision à prendre, pas à contourner.
- Schéma de base **21** (`builder.py:SCHEMA_VERSION`, `PokedexDatabase.VERSION`). La table `evolution` a déjà
  `held_item_id`, `time_of_day`, `known_move_id`, `trade_species_id` ; il manque au moins le lieu d'évolution
  (champ magnétique, Pierre Mousse, Pierre Glacée), le sexe requis, l'espèce présente dans l'équipe.
- `builder_moves.LAST_TYPE_BASED_DAMAGE_CLASS_GENERATION = 3` : la classe par attaque de la 4e génération
  est déjà prévue côté pipeline, à vérifier avec de vraies données et sur la fiche d'attaque.
- `tests/test_future_generations.py` construit déjà les tables Pokémon de `diamond-pearl` (talents de
  Mélofée : Joli Sourire + Garde Magik).
- Sprites : PokeAPI/sprites Noir/Blanc configuré jusqu'au n° 649 (`sprites.LAST_ANIMATED_SPECIES`), donc
  387 à 493 couverts ; 1 à 386 embarqués. Formes embarquées : Zarbi (28), Morphéo, Deoxys
  (`tools/data/pokemon_forms.csv`, `form_sprites.py`).
- Dépendance Python unique en production : `pillow==12.3.0` ; aucune bibliothèque 3D ni numpy.
- RetroAchievements : archives déjà exportées le 12 octobre 2026, non activées — Diamant `9852` (121 succès),
  Perle `25369` (210), Platine `11732` (101). Aucune traduction (`gen12_fr.csv`, `gen3_fr.csv` seulement).
- `docs/generations/generations-suivantes.md` impose, **avant** Diamant/Perle/Platine, de valider un premier
  lieu DS complet sans ROM : image 2D hors ligne, coordonnées des cases, étages, collisions, passages et
  génération reproductible. Aucune source de cartes DS n'est encore déclarée prête.

### Reconnaissance rapide des dépôts pret (arbre seul, sans construction)

| Dépôt | Dernier commit vu | Fichiers | Remarques |
|---|---|---|---|
| `pret/pokeplatinum` | `1dc13dcea40c` (14/10/2026) | 27 668 | ROM US rév. 0 et 1 |
| `pret/pokediamond` | `b623abef1b4d` (11/10/2026) | 33 254 | ROM US Diamant et Perle |

Platine, ressources utiles repérées :

- `res/field/maps/data/map_data_NNN.bin` (666 blocs de terrain : géométrie 3D, permissions des cases,
  hauteurs BDHC, objets posés), `res/field/maps/texture_sets/*.nsbtx` (74) ;
- `res/field/matrices/map_matrix_NNN.json` (291 matrices : `headers`, `altitudes`, `maps`) — la matrice 0
  (Sinnoh) mesure **30 × 30 blocs** de 32 × 32 cases, dont 169 blocs portent un en-tête de lieu ;
- `res/field/area_data/*.json` (jeu de modèles, de textures et d'éclairage par zone),
  `res/field/lighting/*.json`, `res/field/props/{models,model_sets,texture_sets,animations}` ;
- `res/field/events/events_<lieu>.json` (`object_events` avec `x`, `y`, `z` globaux et `hidden_flag`,
  `warp_events`, `coord_events` avec `var`/`value`, `bg_events`) ;
- `res/field/encounters/encounters_<lieu>.json` : herbe (12 emplacements), essaims, remplacements `day` /
  `night`, `radar`, double insertion `ruby`/`sapphire`/`emerald`/`firered`/`leafgreen`, surf et trois cannes,
  plus Grand Marais (six zones), arbres à Miel, Jardin Trophée et canne d'exception (`encdata_ex`) ;
- `res/field/scripts/scripts_<lieu>.s` (1 126), `res/trainers/data/*.json` (928), `res/trainers/classes`,
  `res/pokemon/<espèce>/data.json`, `res/items/data`, `res/text/*.json` (anglais uniquement),
  `res/graphics/field_sprites/npc/*.png` (122), `generated/map_headers.txt` (596 en-têtes),
  `include/data/map_headers.h`, `src/overlay005/{land_data,bdhc,map_prop}.c`.

Diamant/Perle, ressources utiles repérées :

- `files/fielddata/land_data/land_data_release/narc_NNNN.bin` (578), `mapmatrix` (245), `areadata`,
  `build_model` (528 modèles), `eventdata/zone_event_release` (512), `script/scr_seq_release` (1 051 scripts
  **compilés**), `encountdata/d_enc_data` et `p_enc_data` (183 tables par version) ;
- JSON lisibles : `files/poketool/personal/{personal,evo,wotbl,growtbl}.json`,
  `files/poketool/personal_pearl/personal.json`, `files/poketool/trainer/trdata.json` (+ `trpoke`, `trname`),
  `files/poketool/waza/waza_tbl.json`, `files/itemtool/itemdata/item_data.json` ;
- sprites des PNJ en `NCGR`/`NCLR` (`files/data/mmodel`), textes `gmm` ;
- commandes de script en C/assembleur (`arm9/src/scrcmd*.c`, `arm9/asm/scrcmd_*.s`).

### Valeurs et hypothèses à généraliser (à compléter en phase 0 par `rg`)

| Endroit | Hypothèse actuelle |
|---|---|
| `domain/model/Generation.kt`, `GameVersion.kt`, `VersionGroup.kt` | trois générations, onze versions, sept groupes |
| `domain/pokemon/GenerationFeature.kt` | `ABILITIES` sans talent caché ; `ShinyOdds` 1/8 192 |
| `domain/pokemon/CaptureGeneration.kt`, `Gen3CatchRate.kt` | Balls GBA ; pas de Sombre, Soin, Rapide, Parc, Mémoire |
| `domain/guide/Breeding.kt`, `GbaBreeding.kt`, `FriendshipRules.kt` | règles Johto et GBA |
| `domain/guide/Gen3CaptureGoals.kt`, `CaptureGoal.kt`, `Roamers.kt` | objectifs et errants GBA |
| `domain/pokemon/UnownForm.kt`, `PokemonForm.kt` | 28 Zarbi dans les remakes, formes Deoxys/Morphéo |
| `domain/map/MapDestinations.kt`, `MapDetails.kt` (`SpotKind`) | départs et terrains connus |
| `data/guide/AchievementGuides.kt`, `GuideDefinitions.kt` | onze bibliothèques |
| `data/repository/PokemonRepository.kt`, `ui/pokemon/*`, `ui/guide/BreedingViewModel.kt` | cas `GEN3` |
| `data/settings/BackupJson.kt`, `CollectionBackup.kt` | bornes dérivées des jeux et de `maximumSupportedSpecies` |
| `tools/pokemaps_data/games.py` | `PretFormat` GEN1 à GEN3, régions 995 à 999 |
| `tools/pokemaps_data/sprites.py`, `form_sprites.py` | espèces 1 à 386 embarquées ; formes Zarbi/Morphéo/Deoxys |
| `tools/pokemaps_data/maps_*.py`, `maps_render_gen*.py` | cartes 2D en tuiles 8 px (GB) ou métatuiles 16 px (GBA) |
| `tools/spot_editor/version_choice.py` | libellés des groupes connus |
| `tools/tests/test_game_capabilities.py` | matrice des onze versions, `GAMES_IN_PROGRESS == ()` |
| `res/values/strings.xml` `about_credit_pret` | sept dépôts pret |
| `AGENTS.md` §1, `README.md`, `docs/` | onze jeux |

---


---

## Décisions à prendre en phase 0

Chaque décision se coche quand elle est prise, avec sa date et sa justification ; une recommandation est
donnée, elle ne vaut pas décision.

- [ ] **Faisabilité des cartes DS (porte d'entrée de tout le plan).** Rien n'avance au-delà de la phase 1
      tant qu'un lieu DS complet n'est pas validé (voir phase 0, « Prototype »). Si le prototype échoue, arrêter
      et revenir vers l'utilisateur avec les options, sans contournement.
- [ ] **Projection des cartes 3D en image 2D.** Options : vue verticale orthogonale (grille exacte, toits
      visibles, marqueurs simples) ou vue oblique imitant la caméra du jeu (façades visibles, mais décalage
      vertical selon la hauteur, marqueurs à corriger). Recommandation : **vue verticale orthogonale**, une case
      = 16 px comme les cartes GBA et l'éditeur des emplacements, échantillonnage au plus proche (comme la DS),
      à confirmer sur le prototype.
- [ ] **Moteur de rendu.** Options : rasteriseur logiciel écrit dans le pipeline (arithmétique en virgule fixe
      comme la DS, donc octets identiques sous Windows et Linux), ou outil externe de conversion des modèles
      Nitro. Recommandation : **rasteriseur en virgule fixe dans `tools/`**, avec numpy seulement si la mesure
      montre que Pillow seul ne suffit pas (dépendance justifiée par écrit, épinglée dans `requirements.txt`).
      Aucune bibliothèque à réflexion, aucune dépendance au GPU (non reproductible).
- [ ] **Source de Diamant/Perle.** Options : lire les binaires NARC de `pokediamond` (cartes, événements,
      rencontres, scripts compilés), ou ne traiter d'abord que Platine. Recommandation : **Platine d'abord**
      (sources lisibles, comme Émeraude avant Rubis/Saphir), puis Diamant/Perle avec des lecteurs binaires
      bornés et validés ; scripts compilés désassemblés d'après la table de commandes, toute commande inconnue
      arrêtant la lecture.
- [ ] **Famille de cartes** : `diamond-pearl-platinum` commune avec la colonne `version_group` de
      `map_spots.csv` pour ce qui diffère, ou deux familles si les différences de cartes l'imposent. Décider
      après mesure du nombre de blocs de terrain identiques entre les deux dépôts.
- [ ] **Régions** : `SINNOH` (départ Bonaugure, numéro libre 994). Le Souterrain : région séparée (993) ou
      niveau de Sinnoh. Le Monde Distorsion (Platine) : plans par étage, avec note sur la gravité, ou carte
      unique. Les îles d'événement (Île Nouvellune, Paradis Fleuri, noms à relire) : affichées avec « événement externe ».
- [ ] **Matin/jour/nuit** : capacité dérivée des rencontres (`Game.hasTimeOfDay`), voile de lumière repris
      de Johto ou calculé d'après `res/field/lighting`. Lire dans le moteur la règle exacte des remplacements
      `day`/`night` et la place du matin (ne pas la supposer).
- [ ] **Contenus aléatoires ou liés à la sauvegarde** : essaims, Grand Marais, Jardin Trophée, arbres à Miel
      (Goinfrex selon l'identifiant du dresseur), Barpau du Mont Couronné, Pokéradar, double insertion GBA.
      Recommandation : lister les possibilités et probabilités du moteur, ne jamais prédire un tirage ni lire
      une sauvegarde (même règle que les errants et la Grotte Métamo).
- [ ] **Contenus d'événement** (Clé Secrète, Carte Membre, Lettre du Prof, Flûte Azur, Manaphy, Parc des
      Amis, Ranger, GTS) : « événement externe » ou transfert, exclus des objectifs de capture ordinaires.
- [ ] **Périmètre des contenus propres à Sinnoh (phase 8)** : Souterrain (fossiles, sphères, pièges,
      Bases Secrètes), Super Concours, Poffins, baies et paillis, Pokétch, accessoires et sceaux de Ball,
      Tour/Zone de Combat, Villa. Recommandation : données et lieux d'obtention oui, mini-jeux non simulés.
- [ ] **Formes** : Cheniti/Cheniselle, Sancoki/Tritosor, Ceriflor, Motisma (Platine), Giratina, Shaymin,
      Arceus (plaques), Deoxys (changement aux météorites de Voilaroc selon le jeu, à lire), Zarbi (28).
- [ ] **Budget de taille** : la matrice de Sinnoh, si elle était rendue entière à 16 px par case, ferait
      15 360 × 15 360 pixels (236 Mpx, presque deux fois Hoenn d'Émeraude). Mesurer le prototype, rogner aux
      blocs utilisés, signaler tout asset de plus de 5 Mio, rapporter APK, cartes et dépôt Git à chaque phase.
      Le rendu 3D texturé se compresse probablement moins bien que les métatuiles GBA : estimation à chiffrer.
- [ ] **Jaquettes** : Dialga (Diamant), Palkia (Perle), Giratina (Platine) ; couleurs à fixer et relire
      à l'écran en phase 6.
- [ ] **Revanches** : Cherche VS (tables de revanche à lire dans chaque dépôt), toutes les équipes avec
      leur condition, comme pour la 3e génération.

---

## Phase 0 — Reconnaissance, prototype DS et cadrage

Sources :

- [ ] Choisir et épingler `pret/pokediamond` et `pret/pokeplatinum` dans `PRET_COMMITS` (`sources.py`) ;
      vérifier l'absence de licence (comme les autres dépôts pret) et qu'aucune lecture n'exige de ROM, du
      MWCC ni du Nitro SDK.
- [ ] Mesurer `git fetch --depth 1` de chaque dépôt (durée, paquet, sources extraites) ; garder ou ajuster
      `PRET_GIT_TIMEOUT_SECONDS` avec une marge écrite ; vérifier la clé de cache CI
      (`.github/actions/build-database/action.yml`, `data-pipeline.yml`).
- [ ] Recenser, et noter dans ce plan, les fichiers à lire et leurs variantes dans chaque dépôt :
  - [ ] en-têtes de lieux (`include/data/map_headers.h`, `generated/map_headers.txt` ; équivalent Diamant/Perle) :
        matrice, zone, scripts, textes, événements, rencontres, météo, caméra, type de lieu ;
  - [ ] matrices (`headers`, `altitudes`, `maps`), blocs de terrain (`land_data`, `bdhc`, objets posés),
        `area_data`, jeux de textures et de modèles, éclairages ;
  - [ ] permissions des cases (collision, comportement) et comportements de rencontre
        (`src/overlay005/`, constantes de comportements) ;
  - [ ] rencontres (`res/field/encounters`, `encdata_ex` ; `d_enc_data` / `p_enc_data`) et leurs règles dans le
        moteur : remplacements horaires, essaims, radar, double insertion, Grand Marais, arbres à Miel ;
  - [ ] dresseurs et classes, équipes, revanches du Cherche VS, rival selon le starter ;
  - [ ] attaques (puissance, PP, précision, effet, probabilité, classe) ;
  - [ ] objets, Pokémon de base, évolutions, échanges en jeu, tuteurs (Platine), errants, baies et sol meuble ;
  - [ ] scripts (`.s` de Platine, binaires de Diamant/Perle), drapeaux et variables ;
  - [ ] sprites des PNJ et de leurs palettes ; noms et sections de la carte régionale.
- [ ] Identifier la distinction des versions : Diamant ↔ Perle dans `pokediamond` (tables `d_`/`p_`,
      `personal_pearl`, conditions de compilation) ; fixer les symboles de `pret_versions`.
- [ ] Vérifier les icônes pokesprite des objets de la 4e génération et lister les manquants.
- [ ] Vérifier dans PokéAPI épinglé : groupes, versions, Pokédex (`original-sinnoh`, `extended-sinnoh` attendus),
      méthodes de rencontre et d'apprentissage, conditions de rencontre de la 4e génération ; lister celles
      que l'application ne connaît pas (`ObtainMethod`, `LearnMethod`), qui lèveraient une exception.
- [ ] Vérifier dans PokeAPI/sprites la présence des formes de la 4e génération en Noir/Blanc animé et fixe,
      normales et chromatiques.

Prototype de carte DS (porte d'entrée) :

- [ ] Lire un bloc de terrain de Platine : géométrie, matériaux, textures, permissions, hauteurs.
- [ ] Rendre **un lieu complet** : Bonaugure + Route 201 (extérieur sur plusieurs blocs), la maison du joueur
      (intérieur à étages), et une grotte à plusieurs niveaux de hauteur (Mont Couronné ou Grotte Revêche).
- [ ] Prouver sur ce lieu : image 2D lisible, coordonnées des cases alignées sur les événements pret,
      étages et superpositions séparés, collisions et terrains exploitables par l'éditeur, passages reliés.
- [ ] Prouver la reproductibilité : deux générations, Windows et Linux (CI), octets identiques.
- [ ] Mesurer : durée du rendu par bloc, taille WebP des tuiles, extrapolation à toute la matrice de Sinnoh
      et aux intérieurs ; signaler tout dépassement.
- [ ] Faire relire visuellement le prototype à l'utilisateur (captures dans le scratchpad, jamais dans le dépôt).
- [ ] Prendre les décisions ci-dessus, mettre à jour ce plan et
      `docs/generations/generations-suivantes.md` (faisabilité DS validée ou non).

## Phase 1 — Données Pokémon dans l'aperçu

- [ ] `games.py` : `PretFormat.GEN4` (variantes Platine / Diamant-Perle décrites en commentaire),
      `PLATINUM` puis `DIAMOND_PEARL` avec `VersionCover`, `pret_versions`, région `SINNOH`, `national_dex=True` ;
      hors de `GAMES_IN_PROGRESS` tant que le lecteur pret refuse explicitement le format.
- [ ] Espèces 387 à 493 : stats, types, talents (deux au plus, aucun caché), objets tenus, groupes d'œufs,
      taux de capture et cycles lus dans pret (`pret_species.py` étendu au format DS).
- [ ] Évolutions de la 4e génération : objet tenu de jour/de nuit, lieu (champ magnétique du Mont Couronné,
      Pierre Mousse, Pierre Glacée), attaque connue, sexe, espèce dans l'équipe (Rémoraid pour Babimanta),
      échange avec objet. Nouveau schéma si nécessaire (colonnes nommées, commentées). Toute condition inconnue
      de PokéAPI arrête la génération. Comparer aux évolutions du moteur de chaque dépôt.
- [ ] Classe physique/spéciale **par attaque** (`_damage_class`) vérifiée pour les deux groupes ; PP et puissance
      lus dans pret ; nouvelles méthodes d'apprentissage classées ou refusées (`LEARN_METHODS`, `LearnMethod`).
- [ ] Pokédex : Sinnoh puis National dans `builder.pokedex_links` ; `validate` vérifie qu'un Pokémon rencontré
      figure dans un Pokédex de son jeu et qu'aucun Pokédex ne dépasse la génération.
- [ ] `ONE_OFF_METHODS`, `EXTERNAL_EVENT_METHODS`, `EXTERNAL_EVENT_LOCATIONS` : méthodes et lieux de
      la 4e génération classés explicitement (Pokéradar, essaims, double insertion, Miel, Grand Marais,
      canne du Mont Couronné, Parc des Amis…).
- [ ] `transfer_only.csv` : espèces de Sinnoh qui exigent un transfert (Parc des Amis), un échange ou un
      événement, calculé par branche (`validate._check_obtainable`) ; aucune exclusivité Diamant ↔ Perle listée.
- [ ] `name_fixes.csv`, `extra_items.csv`, `item_descriptions.csv` : noms de versions, méthodes, lieux,
      objets relus ; test qu'aucune constante d'objet des deux dépôts n'est inconnue de PokéAPI.
- [ ] `pokemon_forms.csv` et `form_sprites.py` : formes retenues en phase 0, avec leurs versions.
- [ ] Sprites 387 à 493 par le chemin existant ; icônes d'objets manquantes résolues.
- [ ] Tests : talents, évolutions, Pokédex, méthodes classées et refusées, obtention des deux Pokédex
      sur une base réduite ; `test_future_generations.py` avec les vrais `PLATINUM` et `DIAMOND_PEARL`.

## Phase 2 — Lecteurs pret de la 4e génération

Modules sous 600 lignes, nommés par responsabilité (modèle `pret_gen3*.py`) ; chaque lecteur choisit sa
variante par dépôt, toute forme inconnue arrête la lecture.

- [ ] `pret_gen4.py` : façade `Gen4PretRepo`, branchée dans `pret_reader.open_pret` et `DatabaseBuilder`.
- [ ] `pret_gen4_source.py` : lecture bornée des JSON, en-têtes C et constantes de Platine.
- [ ] `pret_gen4_narc.py` (Diamant/Perle) : lecteurs binaires bornés et validés (taille, nombre d'entrées,
      bornes de chaque champ) pour matrices, événements, rencontres, en-têtes.
- [ ] `pret_gen4_maps.py` : en-têtes de lieux, matrices, altitudes, événements (PNJ, warps, déclencheurs,
      panneaux, objets cachés), drapeaux qui cachent les PNJ.
- [ ] `pret_gen4_land.py` : blocs de terrain (permissions, comportements, hauteurs BDHC, objets posés).
- [ ] `pret_gen4_nitro.py` : modèles `NSBMD` et textures `NSBTX` (tous les formats de texture utilisés, refus
      explicite des autres), sous forme de données pures pour le rendu.
- [ ] `pret_gen4_moves.py` : effets, probabilités, PP, puissance ; `move_effects.csv` au format `gen4`.
- [ ] `pret_gen4_scripts.py` : scripts `.s` de Platine ; désassembleur des scripts compilés de Diamant/Perle
      d'après la table des commandes, chaque commande inconnue arrêtant la lecture avec fichier et position.
- [ ] Comparaison Diamant/Perle ↔ Platine des blocs, en-têtes et scripts partagés : seul un test peut
      déclarer un fait commun.
- [ ] Tests unitaires sur extraits réduits (JSON, binaires, modèles) ; tests `pipeline` sur les sources épinglées.
- [ ] Mesures : durée de lecture des deux dépôts, cache, taille des sources.

## Phase 3 — Cartes

- [ ] `maps_render_gen4.py` : rendu des blocs de terrain et des objets posés selon la projection décidée,
      textures à la première image d'animation, transparences ; tuiles WebP de 256 px.
- [ ] Assemblage de Sinnoh depuis la matrice 0, rogné aux blocs utilisés ; intérieurs depuis leurs matrices ;
      plans par étage (`map_plans.csv`), séparation des surfaces superposées (ponts, passerelles, niveaux de grotte).
- [ ] Sprites des PNJ : PNG de Platine ; `NCGR`/`NCLR` de Diamant/Perle décodés, réutilisés seulement si un
      test prouve l'identité des images.
- [ ] `maps.csv` (noms français de la famille ; un nom manquant reste bloquant), `map_plans.csv`,
      `map_anchors.csv`, `map_parents.csv`, `map_connection_skips.csv`, cartes inutilisées écartées.
- [ ] Lieux à relire en particulier : Mont Couronné (nombreux niveaux), Tour Perdue, Vieux Château,
      Bâtiments Galaxie, Île de Fer, Colonnes Lances, Mont Abrupt, Grand Marais, Souterrain ; en Platine,
      Monde Distorsion, Zone de Combat, Villa.
- [ ] Différences Diamant/Perle ↔ Platine : cartes propres à un groupe, blocs différents rendus séparément.
- [ ] Passages sans warp (ascenseurs, téléportations scriptées, Vol, bateau) représentés comme liaisons.
- [ ] Mesurer tuiles, taille des assets, durée de génération et APK ; signaler tout asset de plus de 5 Mio.
- [ ] Tests : assemblages sans recouvrement, warps cohérents, plans, catalogues ; relecture visuelle complète
      des assemblages.

## Phase 4 — Rencontres, terrains et emplacements

- [ ] `pret_gen4_wild.py` + `builder_wild_gen4.py` : herbe, surf, trois cannes, avec taux par emplacement
      du moteur et tables par version (`d_`/`p_` pour Diamant/Perle).
- [ ] Remplacements matin/jour/nuit lus comme le moteur, représentés en conditions (filtre horaire existant).
- [ ] Essaims, Pokéradar, double insertion GBA (cinq cartouches), après Pokédex National : conditions explicites.
- [ ] Grand Marais (zones, jumelles, tirage quotidien listé sans prédiction), Jardin Trophée, arbres à Miel,
      Barpau (cases non placées, note explicite), Zarbi des Ruines Bréchiennes, Souterrain si retenu.
- [ ] Errants : Créfollet, Cresselia, et en Platine les oiseaux légendaires ; routes lues dans le moteur.
- [ ] `maps_terrain_gen4.py` : terrains d'après les comportements des cases (hautes herbes, très hautes herbes,
      eau, grotte, neige, boue, sable…) ; nouveaux `SpotKind` si nécessaire (Kotlin, Python, validation, éditeur).
- [ ] `map_areas.csv`, `extra_areas.csv` : zones PokéAPI encore utilisées (dons, fixes, échanges) reliées aux cartes.
- [ ] Comparaison pret ↔ PokéAPI des rencontres, écarts expliqués (leçon de la pêche absente de PokéAPI).
- [ ] Éditeur PC : groupes `diamond-pearl` / `platinum`, région Sinnoh, nouveaux terrains.
- [ ] Placer et relire les emplacements de la famille dans `map_spots.csv` ; zéro avertissement de terrain
      trop petit, ou décision écrite.
- [ ] `validate.py` : probabilités à 100 % par méthode et par condition, chaque Pokémon du Pokédex obtenable.

## Phase 5 — Dresseurs, personnages, installations et offres

- [ ] `pret_gen4_trainers.py` : équipes, attaques par défaut calculées comme le moteur, objets tenus, combats
      doubles et en duo (avec partenaire), revanches du Cherche VS avec leur condition.
- [ ] Rival de Sinnoh : équipes selon le starter, branchées sur le sélecteur existant ; combats de scène des
      Commandants et de Hélio, Conseil 4, Maître et revanches.
- [ ] `trainer_classes.csv`, `npc_names.csv`, `npc_text_names.csv`, `facility_names.csv` : noms français ;
      un nom manquant arrête la génération.
- [ ] Objets au sol et cachés avec leur drapeau ; jetons cachés du Casino de Voilaroc.
- [ ] Offres : dons d'objets et de Pokémon, œufs (Riolu, Togepi…), boutiques et listes selon les badges,
      échanges, tuteurs (Platine), soins, baies et paillis, fossiles ranimés (Musée de Charbourg), Pension,
      Casino, Maître des Capacités.
- [ ] Conditions de scénario : analyse des branches de scripts sur drapeaux et variables, `story_events.csv` ;
      toute comparaison non décrite bloque sa traduction.
- [ ] Déblocage du Pokédex National relu dans les scripts de chaque jeu, documenté et testé.
- [ ] Pokémon fixes : trio des lacs, Dialga/Palkia, Giratina, Heatran, Regigigas et Regis (Platine), Motisma,
      Spiritomb (Clé de Voûte), légendaires d'événement ; positions, niveaux, conditions, drapeaux de retrait.
- [ ] Monnaies et services nouveaux dans le domaine et les ressources françaises (Points Combat, jetons) ;
      lots du Souterrain si retenus.
- [ ] `npc_duplicates.csv`, `npc_offers.csv`, acteurs de scène : personnages présents à plusieurs étapes,
      offres non lisibles, dons scénarisés.
- [ ] Tests : offres, conditions, drapeaux et variables, dresseurs, parcours intégral des trois versions.

## Phase 6 — Application : prise en charge de la 4e génération et activation

Domaine et données :

- [ ] `Generation.GEN4(4, 493)`, `GameVersion` (`DIAMOND(12)`, `PEARL(13)`, `PLATINUM(14)`, identifiants à
      vérifier dans PokéAPI), `VersionGroup` (`DIAMOND_PEARL`, `PLATINUM`) ; traiter chaque `when` qui échoue.
- [ ] Choix du jeu : section « 4e génération », jaquettes relues à l'écran.
- [ ] `GenerationFeature`, `ShinyOdds` : décisions explicites pour la 4e génération.
- [ ] `ObtainMethod` et filtres de la liste du lieu pour les nouvelles méthodes ; Pokédex et lieu.
- [ ] Capture : `CaptureGeneration.GEN4` (formule lue dans le moteur), Balls Sombre, Soin, Rapide, Parc
      (Parc des Amis), Safari (Grand Marais), Mémoire (événement) et leur contexte (nuit ou grotte, premier tour).
- [ ] Pokédex : Sinnoh puis National, bascule existante ; fiche avec numéro régional puis National.
- [ ] Formes retenues sur la fiche, dans les sprites et la collection ; Zarbi (28) si la phase 0 le confirme.
- [ ] Fiche d'attaque : classe physique/spéciale propre à l'attaque en 4e génération.
- [ ] Évolutions : nouvelles conditions affichées en français (lieu, sexe, équipe, objet de jour/nuit).
- [ ] Mention « événement externe » sur les cartes, rencontres et offres concernées.
- [ ] Sauvegarde de collection : versions 12 à 14, 493 espèces ; import d'un ancien fichier de schéma 1.
- [ ] Schéma : `SCHEMA_VERSION` et version Room alignés, `PokedexSchemaTest` vert.
- [ ] Carte : menu des régions, sélecteurs d'étage et de niveau ; voile et filtre horaires si la capacité est
      présente ; calques nouveaux (arbres à Miel, sol meuble) seulement s'ils portent des données.

Mesures :

- [ ] Temps de trame et mémoire sur la plus grande carte de Sinnoh, sur téléphone, selon `docs/performance.md`
      (build release `.perf`) ; comparer à Hoenn ; corriger avant activation si la fluidité régresse.
- [ ] Mesurer l'index des mentions de guides avec le vrai catalogue DS avant toute décision de le remplacer
      (`generations-suivantes.md`).

Intégration :

- [ ] **Platine** : de `GAMES_IN_PROGRESS` à `GAMES` (génération explicite, `assets.sha256`).
- [ ] **Diamant/Perle** ensuite.
- [ ] Tests JVM : chaque ViewModel modifié teste vide et erreur ; `PokemapsJourneyTest` couvre Platine et
      Diamant ; `MapViewModelTest` couvre le passage Émeraude → Platine et Platine → Diamant ; tests de capture.
- [ ] Essai sur émulateur (captures) et installation `-r -d` sur téléphone sans perte des collections.

## Phase 7 — Guides, succès et outils

- [ ] Ressources des guides de Sinnoh dans des fichiers séparés (`strings_guides_sinnoh*.xml`) ; liens
      `[[pokemon:…]]`, `[[place:…]]` validés par `GuideRepositoryTest`.
- [ ] Sources éditoriales nommées par jeu dans `GuideDefinitions.kt`, citant les fichiers pret aux commits épinglés.
- [ ] Soluces originales de Sinnoh (différences Diamant/Perle ↔ Platine), quêtes annexes, astuces, bugs et
      glitches ; textes originaux, jamais copiés.
- [ ] Calendrier : jours de la semaine et horaires de Sinnoh (événements quotidiens et hebdomadaires lus dans
      les scripts), sans tirage simulé.
- [ ] Succès : `gen4_fr.csv` (ensembles 9852, 25369, 11732), ressources produites par
      `--achievement-resources-only`, `RetroGames`, synchronisation manuelle des quatorze jeux, chapitres liés.
- [ ] `CaptureGoals` : Sinnoh puis National, choix exclusifs (starter, fossiles Kranidos/Dinoclier selon la
      version, Diamant ↔ Perle).
- [ ] Errants : routes et conditions par jeu, observation par cartouche, réglages et sauvegarde.
- [ ] Reproduction : règles de la 4e génération lues dans chaque moteur (IV, Pierre Stase, Encens, Ditto,
      bébés) ; aucun œuf prédit.
- [ ] Bonheur : barème de la 4e génération (massage, coiffeurs, Grelot Zen, Luxe Ball ;
      lieux et effets lus dans les scripts et le moteur).

## Phase 8 — Contenus propres à Sinnoh

Selon le périmètre décidé en phase 0 :

- [ ] Baies : sol meuble, baies initiales, paillis, durées de pousse lues dans le moteur ; calque Baies.
- [ ] Super Concours : catégories, effets de concours des attaques de la 4e génération, affichés sur la fiche.
- [ ] Poffins : saveurs selon les baies, sans simulation du mini-jeu.
- [ ] Souterrain : fossiles et sphères par version, pièges, Bases Secrètes et décorations, lieux d'obtention.
- [ ] Tour de Combat (Diamant/Perle) et Zone de Combat (Platine) : installations décrites, équipes listées
      par série, parcours aléatoires non simulés.
- [ ] Tests du pipeline et JVM de chacune de ces données ; `RELEASE_NOTES.md`.

## Phase 9 — Audit des omissions

Leçon des audits des générations 1 à 3 : ce qui manque se voit tard. Parcourir chaque lieu de chaque version :

- [ ] Chaque dresseur visible a son équipe ; chaque combat de scène est rattaché (rival, Commandants, Hélio,
      Maître, sbires).
- [ ] Chaque don de scène, objet caché, jeton caché et échange est présent et annoté.
- [ ] Chaque table de rencontre pret a sa ligne dans l'application ; aucune pêche ou méthode manquante.
- [ ] Les copies de cartes inutilisées sont écartées ; aucune carte atteignable n'est absente.
- [ ] Les textes des guides sont relus contre les données (noms, lieux, conditions).
- [ ] Les tests de non-régression accompagnent chaque correction.

## Phase 10 — Documentation, publication et bilan

- [ ] `README.md` : quatorze jeux ; `AGENTS.md` §1 (liste des jeux) ; `about_credit_pret` (neuf dépôts pret).
- [ ] `docs/generations/generation-4.md` et ses références techniques par sujet (cartes DS, rencontres,
      personnages, services, guides, contenus) ; `generations-suivantes.md` (HeartGold/SoulSilver comme branche
      suivante) ; `docs/donnees/pipeline.md` (sources, options `--sinnoh-*`, format GEN4) ;
      `docs/fonctionnalites/*.md` ; `docs/developpement.md`.
- [ ] `docs/donnees/sprites-pokemon.md` régénéré (`tools/build_sprite_catalog.py`) : 1 à 493 embarqués.
- [ ] Captures d'écran du README (Sinnoh) sur l'émulateur Android 17.
- [ ] CI : durée de génération, cache et APK mesurés dans `data-pipeline.yml`.
- [ ] `RELEASE_NOTES.md` : une phrase française par changement visible.
- [ ] Relecture visuelle finale des cartes, emplacements et offres ; limites connues écrites.
- [ ] Retirer ce plan du dépôt une fois le bilan reporté dans `docs/` (comme `plan_gen_3.md`), à la demande
      de l'utilisateur.

---

## Contrôle final

- [ ] Plus aucun cas `GEN3` ou borne `386`, `1..11`, `28` restant sans justification (`rg` sur
      `app/src/main/java` et `tools/pokemaps_data`).
- [ ] Aucune méthode de rencontre ou d'apprentissage, classe de dresseur, commande de script, drapeau ou
      variable ignoré en silence : chaque inconnu arrête la génération ou le chargement.
- [ ] Aucun fait de Platine supposé vrai pour Diamant/Perle, ni l'inverse.
- [ ] Bascules entre jeux de branches différentes testées (lieu, surbrillance, horaire).
- [ ] Filtre et voile horaires présents en 4e génération, absents en 3e.
- [ ] Calculateur de capture avec les Balls de la 4e génération.
- [ ] Pokédex Sinnoh puis National, comme dans chaque jeu.
- [ ] Sauvegarde : export/import avec les versions 12 à 14 et 493 espèces ; ancien fichier importé.
- [ ] RetroAchievements des trois jeux vérifiés hors ligne, une lecture par jeu, aucune au lancement.
- [ ] Recherche, fiches et liens carte ↔ Pokédex pour les nouveaux jeux.
- [ ] Sprites 387 à 493, chromatiques, formes, icônes d'objets, PNJ ; `python tools/check_assets.py`.
- [ ] Fichiers sous 600 lignes et fonctions sous 60 lignes, Python comme Kotlin, tests compris.
- [ ] `assets.sha256` à jour, aucun cache ni aperçu versionné, aucun asset disproportionné, tailles rapportées.
- [ ] Aucun service Google Play, interface entièrement en français.
- [ ] Contrôles d'`AGENTS.md` §8 tous verts, y compris `pytest -m pipeline` après génération.

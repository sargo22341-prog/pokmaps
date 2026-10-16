# Sources et pipeline

Les builds et releases utilisent les fichiers versionnés ; `tools/build_data.py` est une opération
explicite de mise à jour. Les règles de reproductibilité et de validation sont dans [AGENTS.md](../../AGENTS.md).

## Sources et sorties

| Source | Usage |
|---|---|
| PokéAPI, export CSV épinglé | Noms français, descriptions, Pokédex, attaques, évolutions et compléments |
| `pret/pokered`, `pokeyellow` | Cartes, personnages, offres et règles des jeux Rouge/Bleu/Jaune |
| `pret/pokegold`, `pokecrystal` | Cartes, scripts et tables sauvages horaires de Johto/Kanto |
| `pret/pokeruby`, `pokeemerald`, `pokefirered` | Cartes, scripts, rencontres, équipes et règles GBA |
| `pret/pokeplatinum`, `pokediamond` | Aperçus Pokémon et cartes DS, lecteurs des modèles, textures, matrices, événements et scripts |
| PokeAPI/sprites | Sprites Pokémon Noir/Blanc normaux et chromatiques |
| pokesprite | Icônes d’objets |
| `tools/data/` | Corrections et compléments éditoriaux relus |
| Archives RetroAchievements et CSV français | Succès officiels et ressources Android traduites |

Commits et URLs : `tools/pokemaps_data/sources.py`. Aucun prélèvement sur pokemaps.net, aucune ROM.
Les sources en cache sont réutilisées ; seules les sources manquantes sont téléchargées.
Les téléchargements sont bornés en taille et durée, avec quatre tentatives HTTP au maximum.

Sorties dans `app/src/main/assets/` : `database/pokedex.db`, `sprites/`, `maps/`, `hoenn.json`, licences
et `assets.sha256`. Les guides sont des définitions Kotlin et ressources françaises ; les succès sont
produits dans `res/values/strings_achievements_<version>.xml` depuis les archives et traductions CSV.
Caches (`tools/.cache`), sources brutes et aperçus (`tools/build/preview`) restent hors Git, sans Git LFS.

Les images sont en WebP sans perte, vérifiées contre leurs sources. Le style Pokémon est identique partout :
animations Noir/Blanc et fixes issus de leur première image. Les espèces 1 à 386 sont embarquées ;
la source est configurée jusqu’à 649. Au-delà, choisir et valider une source avant d’ajouter un jeu.
Zarbi dispose de sprites A–Z, ! et ?, normaux/chromatiques et fixes/animés.
Le [catalogue généré](sprites-pokemon.md) fournit les liens par espèce ; `tools/build_sprite_catalog.py` le reproduit.

## Mettre à jour les données

Depuis la racine, après installation des [dépendances Python](../developpement.md) :

```powershell
python tools/build_data.py
python tools/check_assets.py
cd tools
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
python -m pytest -q -m pipeline
```

Relire et versionner ensemble CSV éditoriaux, scripts concernés, assets et inventaire ; exécuter aussi
les contrôles Android si les données embarquées changent, notamment `PokedexSchemaTest`.
La version du schéma est définie par `builder.py:SCHEMA_VERSION` et `PokedexDatabase.VERSION` : elles doivent
coïncider avec la base générée. Après `VACUUM`, les quatre octets informatifs de version SQLite sont neutralisés
pour éviter une différence due au moteur Python ; les tests comparent tous les octets et l’inventaire complet.
Les tests ordinaires bloquent le réseau et n’exigent pas de cache ; les tests `pipeline` relisent les sources épinglées.

### Génération ciblée

| Option de `tools/build_data.py` | Résultat |
|---|---|
| `--hoenn-maps-only`, `--remake-maps-only` | Cartes de la branche, catalogues associés et inventaire |
| `--hoenn-content-only` | Baies, Concours et décorations Hoenn |
| `--hoenn-fixed-only`, `--remake-fixed-only` | Catalogues des Pokémon fixes |
| `--gen3-encounters-only` | Aperçu GBA des rencontres, sans personnages |
| `--gen3-items-only`, `--gen3-trainers-only` | Aperçu GBA avec objets, puis équipes |
| `--gen3-curation-only` | Rapport éditorial `character_curation.json` |
| `--achievement-resources-only` | Ressources Android des succès depuis les archives locales |
| `--sinnoh-pokemon-only` | Aperçu Pokémon DS dans `sinnoh-pokemon/`, sans cartes ni activation Android |
| `--sinnoh-maps-only` | Deux familles de cartes DS dans `sinnoh-maps/`, sans activation Android |
| `--sinnoh-catalogs-only` | Réexport des catalogues DS existants, après contrôle des sources et de la géométrie |
| `--sinnoh-scenes-only` | Réexport des décors moteur et de tous les calques inférieurs depuis un aperçu validé |
| `--sinnoh-encounters-only` | Rencontres du moteur DS et emplacements dans `sinnoh-encounters/`, après `--sinnoh-maps-only` |

`--assets`, `--preview` et `--cache` choisissent les dossiers. Une génération ciblée de cartes ou de catalogue
ne reconstruit pas la base Room : toute modification affectant celle-ci exige la génération complète.
`--map-workers` choisit de 1 à 8 processus pour les cartes DS (4 par défaut). Les deux familles passent une
vérification de géométrie avant le rendu. Chaque famille remplace ensuite son aperçu après validation complète,
depuis un dossier temporaire ; son ancien aperçu est conservé sous `<famille>.previous-*`. Un échec dans
l’autre famille ne détruit pas les cartes déjà validées. Le réexport des catalogues conserve les tuiles et
refuse une modification des sources, des en-têtes ou des blocs qui exige de refaire les images.
L’export authentifié des archives est une opération distincte, décrite dans
[leur README](../../tools/data/retroachievements/README.md) ; les builds ne l’appellent jamais.

## Où corriger une donnée

| Sujet | Fichiers de `tools/data/` |
|---|---|
| Noms, plans et coordonnées des cartes | `maps.csv`, `map_plans.csv`, `map_anchors.csv`, `map_parents.csv` |
| Connexions, layouts et bordures corrigés | `map_connection_skips.csv`, `map_layouts.csv`, `map_trims.csv` |
| Sélection DS, palettes et niveaux écartés | `map_exclusions_gen4.csv`, `map_texture_bindings_gen4.csv`, `map_level_skips_gen4.csv` |
| Zones de rencontres et placement | `map_areas.csv`, `extra_areas.csv`, `map_spots.csv` |
| Personnages, noms et scènes | `npc_names.csv`, `npc_text_names.csv`, `npc_duplicates.csv`, `scene_actors_gen3.csv` |
| Figurants masqués uniquement sur la carte | `scene_actor_visibility.csv` (scripts et catalogues conservés) |
| Classes, installations et offres | `trainer_classes.csv`, `facility_names.csv`, `npc_offers.csv`, `story_events.csv` |
| Formes, événements externes et objets | `pokemon_forms.csv`, `external_event_maps.csv`, `item_descriptions.csv` |
| Obtention sans transfert et effets d’attaques | `transfer_only.csv`, `move_effects.csv` |

Les taux de capture, cycles d’éclosion et groupes d’œufs viennent du pret de chaque jeu (`pret_species.py`),
pas des valeurs actuelles de PokéAPI. Sexe et courbe d’expérience divergents sont refusés tant que le modèle
les partage entre jeux. Les formes sont dans `pokemon_form` ; la provenance externe utilise des colonnes
dédiées, jamais la détection d’une phrase française. Les validations et leurs tests accompagnent tout nouvel invariant.

### Aperçu Pokémon de Sinnoh

`PLATINUM` puis `DIAMOND_PEARL` sont déclarés au format `GEN4`, hors de `GAMES_IN_PROGRESS` :
la génération générale ne les active pas encore. L’option `--sinnoh-pokemon-only` lit les deux dépôts
épinglés, sans ROM, et génère une base et les sprites normaux/chromatiques des 493 espèces dans l’aperçu.
Les variantes de Perle sont lues séparément pour les objets tenus ; un test compare leurs autres données à Diamant.

Les statistiques, types, talents, objets tenus, capture et reproduction viennent des données personnelles DS.
Les évolutions PokéAPI sont comparées aux deux tables pret. Le schéma 22 conserve les conditions supplémentaires
dans `evolution_requirement` : lieu, sexe, espèce dans l’équipe, proximité d’une pierre et formes de départ/arrivée
(identifiants PokéAPI). Le moteur de chaque dépôt fournit le seuil de bonheur.

La table préparatoire `ds_move` contient puissance, PP, précision, type et classe par attaque ; `move_version_group`
porte en plus les effets, relus dans `move_effects.csv` au format `gen4` (clé : numéro d’effet du moteur, commun aux
deux dépôts). Les rencontres aléatoires viennent du moteur (« Rencontres DS ») ; les dons, fixes, échanges et
errants restent ceux de PokéAPI, avec une correction de Giratina dans Diamant/Perle vérifiée dans le script compilé
épinglé. Les méthodes et conditions inconnues arrêtent l’export. Cet aperçu n’est pas une base distribuable dans
l’application.

### Rencontres DS

`pret_gen4_wild_rules.py` lit les règles sauvages dans le C de Platine et `pret_gen4_wild_rules_dp.py` dans
l’assembleur de Diamant/Perle, dont chaque fragment est vérifié instruction par instruction : probabilités des
emplacements (12 d’herbe, 5 de surf et 5 par canne), emplacements remplacés (essaim, heure, Pokéradar, Pokémon du
jour, double insertion), comportements des cases, lieux d’essaim, arbres à Miel, Barpau, errants et formes. Un test
compare les deux lectures. `pret_gen4_wild_extra.py` lit l’archive `encdata_ex` (arbres à Miel, Jardin Trophée,
Grand Marais, Barpau).

`pret_gen4_wild.py` traduit chaque remplacement en condition PokéAPI : le matin garde la table de base, le jour et le
crépuscule prennent `day`, la nuit `night` ; l’essaim ne vaut que dans les lieux de la liste du moteur, le Pokéradar
que dans les lieux à hautes herbes. Une condition qui ne change pas l’espèce d’un emplacement est omise. Les Pokémon
du jour du Grand Marais et du Jardin Trophée ne sont jamais prédits : chaque entrée de la liste reçoit sa part de la
probabilité des emplacements remplacés. `builder_wild_gen4.py` remplace marche, surf, cannes et arbres à Miel de
PokéAPI et vérifie contre le moteur Barpau et les errants de PokéAPI. `validate_encounters_gen4.py` exige 100 % pour
chaque combinaison de conditions.

`compare_wild_gen4.py` compare ces tables à PokéAPI par combinaison de conditions, donc par ce que le joueur
rencontre ; `encounter_comparison.json` liste les écarts de l’aperçu. Ils viennent tous de zones regroupées
autrement (`extra_areas.csv`), du Pokémon du jour en probabilité moyenne et d’erreurs de PokéAPI (Pokéradar sans
hautes herbes, essaims hors de la liste du moteur) ; un test `pipeline` les classe et refuse tout autre écart.

`maps_terrain_gen4.py` déduit les terrains des comportements de cases (herbes, sol, eau) et des arbres à Miel posés ;
`maps_data_gen4.py` place les emplacements sur l’image oblique. Une case à plusieurs niveaux (pont, passerelle) garde
son terrain mais ne reçoit pas d’emplacement.

### Lecteurs DS

`pret_gen4.Gen4PretRepo` (choisi par `open_pret`) lit les deux dépôts dans un même modèle de données : en-têtes de
lieux, matrices, événements, zones, objets posés, éclairages, caméras, tables de rencontres brutes, blocs de terrain
(attributs, objets, hauteurs BDHC), modèles et textures Nitro, attaques et scripts. Platine se lit dans ses JSON,
en-têtes C et macros (`pret_gen4_maps.py`, `pret_gen4_events.py`, `pret_gen4_scripts.py`) ; Diamant/Perle dans
ses fichiers extraits (`pret_gen4_narc.py`) et dans le moteur, en C ou en assembleur (`pret_gen4_maps_dp.py`,
`pret_gen4_script_commands.py`). La forme des arguments de chaque commande de script compilé se lit dans la
fonction du moteur ; le désassembleur (`pret_gen4_script_binary.py`) suit le flux depuis les points d’entrée. Les
formats sont refusés dès qu’ils sortent de ce que les deux dépôts emploient (textures 4 × 4 et directes, commandes
GX ou de script inconnues, tailles incohérentes).

### Cartes préparatoires de Sinnoh

`maps_gen4.py` assemble séparément Platine et Diamant/Perle depuis leurs matrices pret. Sinnoh et le Grand Marais
gardent leurs en-têtes de blocs ; les autres matrices donnent les intérieurs et les étages. `maps.csv` fournit
tous les noms français, les plans éditoriaux restent dans `map_plans.csv`, et `map_parents.csv` décrit les origines.
Les matrices donnent déjà les positions : aucun ancrage géométrique artificiel n’est nécessaire.
`map_exclusions_gen4.csv` écarte explicitement les copies inutilisées, avec leur raison ; les anciennes portes
qui les visent restent tracées dans `map_connection_skips.csv` et dans les liaisons non navigables.
`map_level_skips_gen4.csv` écarte les plans BDHC qui ne correspondent pas à un étage accessible ; le réexport
éditorial retire leurs calques obsolètes sans modifier les images conservées.
Le Passage Marin de Diamant/Perle reste retenu malgré son nom source `MAP_ROUTE_231_UNUSED` : son en-tête est
référencé par la matrice 0 et porte la zone de textures du passage effectivement présent dans le jeu.

`maps_render_gen4` rend terrain et objets posés ; `maps_geometry_gen4` traite les nœuds et la pile SBC ;
`maps_raster_gen4` projette les triangles en arithmétique entière (profondeur, textures au plus proche,
transparence). Les valeurs de cotangente sont fixes, relues contre les caméras des sources. Les images sont
découpées en cadres bornés, puis en WebP sans perte de 256 pixels ; aucune image régionale entière n’est chargée.
La pyramide de zoom est construite depuis les tuiles du niveau supérieur.

`maps_dynamic_gen4.py` lit aussi le décor chargé par le moteur hors des blocs : étages et plateformes de
Joliberges, engrenages de Rivamar à l’état zéro, eau de Verchamps à son niveau initial, horloge de Vestigion
dans Platine, cloisons et ascenseurs d’arènes dans Diamant/Perle, tramway du Grand Marais et plateforme de
l’Île de Fer. `dynamic-props.json` conserve leurs positions et leur provenance. Les mécanismes ne sont pas
animés et aucune sauvegarde n’est simulée ; la Villa garde son état vide, avant achat du mobilier.

Les textures automatiques NSBTP et NSBTA sont évaluées à l’image zéro (`pret_gen4_animation.py`,
`pret_gen4_prop_animations.py`) ; les animations articulées ne sont pas jouées, le décor garde sa pose de modèle.
Les deux jeux de textures chargés par zone fournissent terrain et objets ; les noms de palettes manquants
sont corrigés explicitement dans `map_texture_bindings_gen4.csv`. Un bloc de remplissage sans en-tête prend
la zone nommée compatible la plus proche, dans un ordre stable. Un matériau ou une commande inconnu arrête l’export.

Le BDHC fournit les niveaux praticables superposés. Les surfaces d’au moins quatre cases libres contiguës,
séparées d’au moins une case en hauteur, produisent un calque inférieur ; les petites surfaces de mobilier
et les cases en collision ne créent pas d’étage. `levels.json` conserve cases et plafonds. Les calques inférieurs
partagent exactement le cadre de leur base ; `matrices.json` indique les rectangles qu’ils remplacent.
Tous les niveaux superposés sont conservés, y compris les quatre de Joliberges. Un objet appartenant à
l’étage supérieur est retiré entièrement du plan inférieur, afin que sa face inférieure ne masque pas le sol.
Le Monde Distorsion conserve ses plans et ses liaisons, sans simulation de la gravité ni des plateformes mobiles.

Chaque famille contient `catalog.tsv`, `passages.tsv`, `events.json`, `matrices.json`, `levels.json`,
les images de PNJ et leur provenance (`sprites.json`), ainsi qu’un inventaire `assets.sha256`.
Les sprites PNG de Platine et les NSBTX de Diamant/Perle sont lus séparément ; les couleurs invisibles sous
l’alpha nul sont normalisées avant comparaison. Les apparences variables et les objets à modèle 3D restent
explicitement distingués des sprites. Les liaisons comprennent warps, ascenseurs, scripts, bateau, Vol,
plateformes du Monde Distorsion, destinations possibles de la Grotte Retour et accès au Souterrain par le
Kit Explorateur. L’arrivée souterraine et le retour en surface dépendent de la position mémorisée ; aucun
tirage ni déplacement du joueur n’est simulé.

Après génération :

```powershell
python tools/check_assets.py --sinnoh-maps tools/build/preview/sinnoh-maps
python tools/review_gen4_maps.py
```

La relecture couvre chaque lieu du catalogue, chaque bloc possédant un niveau inférieur et les seize modèles
de blocs du Souterrain en détail. Arial (Windows/macOS) ou DejaVu Sans (Linux) fournit les accents des libellés.
Les planches et leur index restent dans `tools/build/scratchpad/gen4-map-review/`. Les durées et tailles sont
mesurées dans l’aperçu (`generation-report.json`), hors des inventaires des familles. Les jeux DS restent
hors de `GAMES_IN_PROGRESS` jusqu’à l’intégration des rencontres, personnages et écrans : ces cartes ne sont
pas encore distribuées dans l’APK normal.

Les formes de Sinnoh suivent leurs versions dans `pokemon_forms.csv`. Les formes Fée et ??? d’Arceus sont exclues :
la première est postérieure à ces jeux et la seconde n’a pas de sprite Noir/Blanc épinglé.

## Éditeur des emplacements

```powershell
python tools/map_editor.py
# Pour un aperçu explicitement généré :
python tools/map_editor.py --assets tools/build/preview/gen3-encounters
python tools/map_editor.py --assets tools/build/preview/sinnoh-encounters
```

L’éditeur lit l’aperçu lorsqu’un jeu est en cours d’intégration, sinon les assets distribués.
Il utilise la base, les images et les sources pret déjà présentes ; aucun téléchargement.
Choisir famille de jeux, région, lieu et terrain. Clic gauche : ajouter/retirer un point centré sur une case
de 16 px ; clic droit glissé : déplacer ; molette : zoomer ; « Ajuster » : cadrer le plan.
Les calques et l’aperçu des sprites permettent de relire l’espace réellement disponible.

« Carte affichée » choisit la variante du plan. Les points sont communs à la famille ;
« Points uniquement pour … » crée une liste propre au groupe qui remplace les points communs de ce terrain.
Un jeu sans ce lieu ne participe pas à sa validation. Les retouches restent en attente entre les cartes.
Les clics hors terrain sont refusés ; les anciens points invalides restent visibles et bloquent l’enregistrement.
La liste d’erreurs ouvre et centre le point fautif. Le rapport local est `tools/build/map_spot_errors.json`.

« Enregistrer toutes les cartes » valide et écrit uniquement les terrains modifiés dans `map_spots.csv`
(`family,map_identifier,kind,x,y,version_group`). Un groupe vide signifie une portée commune ; des coordonnées
vides marquent un terrain vide. Ce bouton ne génère ni n’installe l’application : lancer ensuite le pipeline complet.
Un terrain sans point est une erreur ; un terrain trop petit conserve un avertissement visible.
L’application choisit un Pokémon par point et garde les autres dans la liste du lieu. Les exceptions relues sont
conservées dans les références de rencontres [Hoenn](../generations/rencontres-hoenn.md) et
[remakes](../generations/rencontres-remake-1g.md).

## Ajouter un jeu

1. Valider d’abord la faisabilité de ses cartes ; pour la DS, lire les
   [prérequis](../generations/generations-suivantes.md).
2. Déclarer le jeu dans `games.py:GAMES_IN_PROGRESS`, puis adapter lecteur pret, régions, départ,
   variantes de format, rendu et noms français. L’aperçu inclut tous les jeux, sans activer les nouveaux.
3. Lire ses rencontres, offres, règles Pokémon, effets d’attaques et formes ; refuser toute donnée inconnue.
4. Déclarer `Generation`, `GameVersion`, `VersionGroup`, méthodes d’obtention et jaquette Android ;
   décider explicitement capture, bonheur, reproduction, Zarbi et guides. Ne pas déduire ces règles d’un identifiant.
5. Compléter les matrices de capacités Python/Kotlin, les validations et les tests, puis relire les cartes.
6. Passer dans `GAMES` seulement quand base, interface et contrôles sont prêts. `GAMES_IN_PROGRESS` est actuellement
   vide.

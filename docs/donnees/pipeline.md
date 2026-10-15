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

`--assets`, `--preview` et `--cache` choisissent les dossiers. Une génération ciblée de cartes ou de catalogue
ne reconstruit pas la base Room : toute modification affectant celle-ci exige la génération complète.
L’export authentifié des archives est une opération distincte, décrite dans
[leur README](../../tools/data/retroachievements/README.md) ; les builds ne l’appellent jamais.

## Où corriger une donnée

| Sujet | Fichiers de `tools/data/` |
|---|---|
| Noms, plans et coordonnées des cartes | `maps.csv`, `map_plans.csv`, `map_anchors.csv`, `map_parents.csv` |
| Connexions, layouts et bordures corrigés | `map_connection_skips.csv`, `map_layouts.csv`, `map_trims.csv` |
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

## Éditeur des emplacements

```powershell
python tools/map_editor.py
# Pour un aperçu explicitement généré :
python tools/map_editor.py --assets tools/build/preview/gen3-encounters
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

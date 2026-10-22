# Plan d’intégration — Pokémon Or HeartGold et Argent SoulSilver

Document de travail établi le 21 octobre 2026, à partir du dépôt actuel.
Objectif : intégrer les deux remakes DS avec le même niveau de finition que les jeux déjà distribués.
Ce document prépare le travail ; il ne déclare aucun remake disponible dans l’application.

## 1. Principes et périmètre

- Or HeartGold et Argent SoulSilver appartiennent à la génération 4, avec une branche propre.
- Couvrir Johto **et Kanto**, l’aventure principale, l’après-Ligue et les contenus particuliers des remakes.
- Or, Argent et Cristal servent à retrouver des lieux, noms et sujets à vérifier. Leurs cartes, scripts,
  probabilités, équipes, objets et règles ne constituent jamais une valeur de remplacement pour HGSS.
- Une ressemblance avec Platine ne prouve pas davantage une règle commune.
- Rester entièrement hors ligne, sauf la synchronisation RetroAchievements déjà autorisée.
- Garder les quatorze jeux actuels utilisables et conserver leurs préférences et sauvegardes.
- Livrer des cartes lisibles, des fiches fiables et une navigation réciproque carte/Pokédex/guides.
- Ne pas simuler le déplacement du joueur, les mini-jeux, une sauvegarde de cartouche ou les tirages aléatoires.
- L’intégration comprend la documentation des conditions d’accès externes ; elle ne promet pas de rendre
  aujourd’hui disponibles les anciennes distributions.

## 2. État constaté dans le dépôt

### Architecture et activation

`AGENTS.md` fixe le sens UI → cas d’usage → données, avec modèles et règles métier purs.
Les composables ne doivent lire ni base ni assets ; les ViewModels ne dépendent pas de `data`.

| Point d’entrée | Situation actuelle et conséquence |
|---|---|
| `tools/pokemaps_data/games.py` | `GAMES` contient 14 versions ; `GAMES_IN_PROGRESS` est vide. |
| `Game`, `Region`, `VersionCover` | Régions, famille, mascotte et génération d’origine déjà modélisées. |
| `tools/pokemaps_data/sources.py` | PokéAPI et neuf dépôts pret sont épinglés ; `pokeheartgold` est absent. |
| `tools/build_data.py` | Sépare déjà génération distribuée et aperçus préparatoires. |
| `domain/model/Generation.kt` | `GEN4` existe déjà et fixe le plafond national à 493 espèces. |
| `domain/model/GameVersion.kt` | Dernière version reconnue : Platine, identifiant 14. |
| `domain/model/VersionGroup.kt` | Aucun groupe HeartGold/SoulSilver. |
| `builder.py`, `data/db/PokedexDatabase.kt` | Schéma Python et Room actuellement en version 23. |

Les chemins Kotlin de ce document sont relatifs à
`app/src/main/java/org/opensources/pokmaps/`, sauf indication contraire.

### Acquis à réutiliser avec vérification

- Génération 2 : deux régions, noms français, horaires, arbres, rochers, concours et parcours de Johto/Kanto.
  Références : `docs/generations/generation-2.md`, `builder_wild_gen2.py`, `maps_render_gen2.py`.
- Sinnoh : lecteurs Nitro, modèles et textures, matrices, projection oblique, hauteurs BDHC,
  assemblages, étages et plans inférieurs, personnages, scripts, offres et export vers les tables communes.
- Modules concernés : `pret_gen4*.py`, `maps_*gen4.py`, `builder_wild_gen4.py`,
  `validate_*gen4.py`, `preview_*gen4.py`, `compare_wild_gen4.py`.
- Android : navigation et filtres DS, formes, Zarbi, National/régional, guides,
  outils de capture et reproduction, suivi des errants et sauvegarde JSON.
- Éditeur PC : `tools/spot_editor/`, ouvert par `tools/map_editor.py`, avec lecture d’aperçus via `--assets`.

### Couplages à traiter explicitement

`Gen4PretRepo` ne reconnaît que Platine et Diamant/Perle. De nombreuses propriétés choisissent
`platinum` ou, sinon, Diamant/Perle. Ajouter HGSS à une liste sans changer ces choix lirait le mauvais format.
`maps_gen4.py` impose aussi un dossier nommé `sinnoh-maps` et parcourt les seuls jeux DS actuels.
La sélection du commit dans ses catalogues dépend encore de ce choix binaire.

`encounter_methods_gen4.py` définit une taxonomie de Sinnoh, pas une taxonomie universelle DS.
`CaptureGeneration.GEN4.balls` reprend les Balls GBA et trois ajouts DS ; il ne propose pas les Balls
Noigrumes. Une décision fondée uniquement sur la génération est donc insuffisante pour HGSS.
`BackupJson.kt` utilise une clé `sinnohRoamers` et `CollectionBackup.kt` appelle
`SinnohRoamerObservations` : étendre ce suivi exige une compatibilité explicite des anciens exports.

Les noms `sinnoh`, `gen4` et `remake` ne sont pas interchangeables : les options actuelles
`--remake-maps-only` et `--remake-fixed-only` concernent Rouge Feu/Vert Feuille.

### Plans antérieurs et documentation

Aucun ancien plan d’intégration n’a été trouvé parmi les fichiers suivis parcourus à la racine.
Les références exploitables sont les documents actuels, accessibles depuis `docs/README.md`,
notamment `docs/donnees/pipeline.md`, `generation-4.md` et `generations-suivantes.md`.
Ce dernier exige déjà la validation d’un premier lieu DS complet avant une nouvelle branche.

## 3. Sources et règles de preuve

### Source principale à qualifier

Le dépôt [pret/pokeheartgold](https://github.com/pret/pokeheartgold) est la source candidate pour les deux jeux.
Son [README](https://github.com/pret/pokeheartgold/blob/master/README.md), consulté pour ce plan,
annonce les deux variantes américaines et un travail encore en cours, avec une structure susceptible de changer.
Cela confirme le candidat, **pas** l’exhaustivité des ressources nécessaires sans ROM.

Première session : choisir un commit exact, inventorier les fichiers réellement disponibles et les différences
HeartGold/SoulSilver. Les chemins internes et formats HGSS restent à établir au commit retenu.
Ne pas figer dans ce plan des noms d’archives non vérifiés. Ne pas compiler le jeu ni réclamer une ROM.
Si une ressource requiert une extraction externe absente du dépôt, documenter précisément la lacune et rechercher
une source compatible avec les règles du projet avant de poursuivre la partie concernée.

### Hiérarchie des données

| Donnée | Autorité et contrôle |
|---|---|
| Cartes, collisions, scripts, objets et équipes | HGSS épinglé ; provenance fichier/table/entrée. |
| Rencontres et probabilités conditionnelles | Tables **et moteur HGSS** ; expliquer les écarts avec PokéAPI. |
| Statistiques, talents, capture, reproduction, attaques | Données et règles HGSS ; comparaison PokéAPI. |
| Noms français, textes et numérotation du Pokédex | CSV PokéAPI épinglés, puis corrections françaises relues. |
| Sprites Pokémon | Conserver la convention Noir/Blanc normale et chromatique du dépôt. |
| Sprites de terrain et décors | Ressources HGSS, séparées des sprites de fiches Pokémon. |
| Compléments éditoriaux | `tools/data/`, avec justification et provenance ; jamais dans une sortie générée. |

Pour chaque extraction, conserver jeu, commit, identifiant natif, transformation et éventuelle correction.
Une donnée manquante provoque une erreur nommée ou un jalon bloqué ; aucune récupération automatique depuis GSC.
Classer les éléments : vérifié dans la source, complément éditorial recoupé, ou question à résoudre.
L’activation finale interdit les questions non résolues qui affectent les contenus promis.

Les identifiants attendus sont `heartgold`, `soulsilver`, groupe `heartgold-soulsilver`, versions 15 et 16.
Les confirmer dans les CSV PokéAPI épinglés avant déclaration ; ne pas déduire les règles de ces nombres.
Le Pokédex régional attendu est Johto remanié, 256 entrées, et le National 493 : contrôler rangs et contenu
dans les sources, sans réutiliser le régional de 251 espèces de GSC.

### Succès déjà présents

`tools/data/retroachievements/index.json` référence l’archive commune `7212.json` avec 136 succès,
ainsi que `39076.json`, SoulSilver, sans succès dans cet export.
Ce sont les nombres de l’archive locale, pas une vérification de l’état du service au jour de l’activation.
Inspecter les archives et les traductions existantes avant tout nouvel export.
Décider et tester l’association des deux cartouches au jeu RetroAchievements commun ; ne pas confondre
le set partagé et l’entrée SoulSilver vide. Aucun identifiant de succès ne doit être réinventé.

## 4. Conception technique proposée

### Déclaration et isolement

Ajouter `HEARTGOLD_SOULSILVER` dans `games.py`, d’abord dans `GAMES_IN_PROGRESS` seulement :
famille `heartgold-soulsilver`, génération 4, `remake_generation=2`, National activable,
mascottes Ho-Oh et Lugia, Johto puis Kanto, départ Bourg Geon.
Créer des identifiants régionaux composites sans collision avec les cartes existantes.
Une famille commune reste à confirmer par comparaison des géométries des deux versions ; les variantes
de rencontres, événements et accès doivent rester identifiées par cartouche.

Conserver `PretFormat.GEN4` si le contrat DS convient, avec une variante HGSS explicite.
Extraire les lecteurs propres aux jeux en modules nommés par responsabilité, par exemple
`pret_hgss_maps.py`, `pret_hgss_wild.py`, `pret_hgss_scripts.py`.
Ce sont des noms proposés, pas des fichiers déjà présents.
Remplacer les choix binaires Platine/DP aux frontières touchées ; ne pas construire un moteur universel
de désassemblage et ne pas réorganiser tout le pipeline.
Réutiliser les modèles et codecs DS seulement après tests de format et de coordonnées.

### Aperçus et commandes

Proposer des options **nouvelles, à implémenter**, indépendantes des options Sinnoh et RF/VF :

| Option proposée | Sortie sous `tools/build/preview/` |
|---|---|
| `--hgss-pokemon-only` | `hgss-pokemon/` : données Pokémon et contrôle des sprites. |
| `--hgss-maps-only` | `hgss-maps/` : tuiles, lieux, étages, passages et catalogues. |
| `--hgss-encounters-only` | `hgss-encounters/` : rencontres, conditions et points de terrain. |
| `--hgss-characters-only` | `hgss-characters/` : personnages, combats, objets, fixes et offres. |
| `--hgss-content-only` | `hgss-content/` : catalogues particuliers aux remakes. |

Chaque étape vérifie le commit et les empreintes de ses prérequis. Une sortie périmée est refusée.
Réutiliser le stockage temporaire et le remplacement après validation ; un échec préserve l’aperçu valide.
Garder téléchargements, parcours, désassemblage et processus bornés ; cache par contenu et rapport de durée/taille.
Le rendu HGSS ne doit pas régénérer Sinnoh à chaque session. Mesurer la réutilisation des codecs et caches.

### Cartes, régions et navigation

Valider d’abord Bourg Geon, un intérieur relié et un passage vers une route, dans les deux cartouches.
Le lot doit prouver image, cases, collision, altitude, personnages, entrée/sortie et reproductibilité.
Ajouter ensuite un lieu à étage/pont pour éprouver les plans inférieurs avant le rendu global.

Inventorier toutes les cartes utiles, leur région, leur nom français et leur variante de scénario.
Assembler Johto et Kanto sans reprendre les coordonnées Game Boy. Adapter les CSV existants par famille,
dont `maps.csv`, `map_areas.csv`, `map_anchors.csv`, `map_plans.csv`, `map_parents.csv`,
`map_assemblies_gen4.csv` et les corrections DS nécessaires.
Ne pas forcer une particularité HGSS dans une colonne conçue exclusivement pour Sinnoh.

Couvrir les liaisons ordinaires et spéciales : portes, escaliers, grottes, bateaux, train et déplacements
scriptés réellement présents. Conserver la condition d’accès et distinguer destination fixe et variable.
Relire notamment les lieux remaniés de Kanto, les Ruines d’Alpha, les Îles Écume, les Tourb’Îles,
le Mont Argenté, les installations de combat et les nouveaux lieux recensés dans les sources.
Les décors dynamiques gardent un état initial documenté ; les interactions restent compréhensibles dans les guides.

### Rencontres et conditions

Séparer tables aléatoires, uniques, dons, échanges, errants et obtentions externes.
Extraire les remplacements dans l’ordre du moteur. Calculer les probabilités pour **une configuration
compatible** de conditions, sans additionner des alternatives mutuellement exclusives.
Faire un rapport comparatif PokéAPI ; chaque divergence doit être expliquée et testée.

Inventaire HGSS à confirmer dans le moteur, puis à couvrir :

- marche, surf, cannes, matin/jour/nuit et essaims ;
- arbres à Coup d’Boule, arbres particuliers et Éclate-Roc ;
- radio et journées associées, sons de Hoenn/Sinnoh et déblocages ;
- Concours de capture d’insectes, jours, National et variantes de tables ;
- Parc Safari : zones, objets/blocs, seuils et maturation en jours ;
- Pokémon fixes et errants, scénarios, réapparitions et différences entre cartouches ;
- échanges avec les PNJ, dons, œufs, fossiles, récompenses et starters supplémentaires ;
- Pokéwalker, transferts, distributions et événements conditionnés par un Pokémon provenant d’ailleurs.

Le Parc Safari nécessite un modèle explicite des configurations : ne pas développer toutes les combinaisons
si elles explosent. Exposer exigences, candidats et taux conditionnels vérifiés, avec une borne démontrée.
Ne pas afficher une probabilité inconditionnelle inventée lorsque la configuration manque.
Pour radio, arbres et concours, afficher les conditions utiles sans prétendre prédire le résultat.
Le Pokéwalker peut avoir un catalogue propre : ne pas placer artificiellement ses rencontres sur Johto.
Événement externe et accessoire doivent rester des catégories distinctes.

Étendre méthodes, conditions, filtres et traductions des deux côtés Python/Kotlin.
Ne pas activer par héritage les filtres Pokéradar, double insertion ou Miel de Sinnoh.
Valider les points via terrain et projection HGSS ; ouvrir l’aperçu dans l’éditeur PC pour la curation.

### Pokémon, combats et outils

Importer les données du groupe HGSS : statistiques historiques, types, talents, objets tenus,
attaques apprises, CT/CS, tuteurs, évolutions et formes disponibles par cartouche.
Les 493 sprites d’espèces déjà distribués ne dispensent pas du contrôle des formes et de leurs droits d’accès.
Vérifier les formes de Zarbi et les conditions de déblocage propres aux Ruines d’Alpha.
Conserver la classe physique/spéciale de chaque attaque DS.

Établir une matrice de règles par `VersionGroup` :

| Sujet | Décision à prouver dans HGSS |
|---|---|
| Capture | Balls Noigrumes, modificateurs, cas limites, Safari, concours et Parc des Amis. |
| Bonheur | Valeurs initiales, gains/pertes, objets et seuils d’évolution. |
| Reproduction | Héritage IV/natures, objets Pouvoir, Pierre Stase, talents, attaques et encens. |
| Évolution | Lieux et méthodes indisponibles localement, échanges et transferts nécessaires. |
| Collection | Formes locales, régional/National, indépendance par cartouche et captures partagées configurables. |

Ajouter un contexte de jeu au calculateur de capture là où `CaptureGeneration` ne suffit plus.
Réutiliser les formules DS communes après comparaison ; ne pas réutiliser les bugs des Balls de GSC.
Ne pas étendre `SinnohBreeding` par simple alias : isoler seulement les règles effectivement communes.

### Personnages, objets et services

Lire scripts, conditions et drapeaux HGSS pour les équipes initiales, équipes selon starter,
combats de scénario, Ligue, champions et revanches. Étudier le Pokématos et ses rendez-vous,
sans transposer le Cherche VS de Sinnoh.
Garder chaque combat et son étape, éviter les doublons de scènes et placer les acteurs loin des passages.
Éprouver sprites de terrain, orientations, Pokémon accompagnateurs et acteurs temporaires ;
ne pas ajouter de marqueur sans interaction utile.

Extraire objets visibles/cachés, quantités, réapparitions, CT/CS et conditions d’accès.
Couvrir boutiques, Pension, échanges, tuteurs, soins, fossiles, Noigrumes et fabrication de Balls,
récompenses et monnaies spécifiques. Réutiliser les offres et composants de paiement du schéma actuel
si leur sémantique correspond ; garder coût, délai et contrepartie séparés.
Examiner les différences régionales : la source candidate est américaine ; le Casino/Voltorbataille
et les autres variantes doivent correspondre à l’édition documentée pour l’utilisateur français.

### Guides et contenus propres aux remakes

Prévoir une soluce française adaptée à chaque version jusqu’à Red et à l’après-jeu,
des quêtes, un calendrier hebdomadaire et des objectifs de collection calculés par cartouche.
Ne pas copier les guides GSC sans relecture de chaque étape, équipe et récompense.

Inventorier et documenter : Pokéathlon, Noigrumes/Noigrumes à boire, Parc Safari,
Pokéwalker et parcours externes, Zone de Combat, concours, radio, Pokématos,
événements de scénario et distributions, photos et autres activités réellement présentes.
Réutiliser les catalogues de Platine pour les installations seulement après comparaison des règles et données.
Prévoir des catalogues structurés propres à HGSS lorsque les données dépassent un texte de guide.
Ils suivent repository → cas d’usage → UiState ; aucune lecture JSON dans un composable.
Pas de simulation des mini-jeux ; tableaux, conditions, récompenses et outils déterministes suffisent.

Les objectifs « cartouche seule » doivent distinguer starters incompatibles, échanges, accessoires,
transferts et distributions. Une disponibilité globale de l’espèce ne prouve pas sa capturabilité locale.
Traduire les succès officiels, avec identifiants stables et association des versions testée.

### Android, base et sauvegardes

Ajouter les versions et le groupe aux enums ; réutiliser `Generation.GEN4`.
Présenter les remakes de génération 2 selon la convention déjà utilisée pour RF/VF.
Vérifier jaquettes, changement de jeu, départ de famille, choix Johto/Kanto, retour depuis une fiche
absente du nouveau catalogue, recherche, objets, personnages, guides et filtres horaires.
Tout texte visible vient des ressources françaises ; conserver accessibilité et zones tactiles de 48 dp.

Auditer toutes les décisions sur `VersionGroup`, les matrices de capacités Python/Kotlin et les limites
codées sur les listes actuelles de jeux. Les branches exhaustives doivent décider HGSS explicitement.
Ne pas ajouter de menus de réglage sans besoin utilisateur.

Conserver la structure SQL actuelle quand elle exprime correctement les nouvelles données.
Toute extension nécessaire des conditions/offres/catalogues est décidée avec son invariant et ses tests.
Si SQL change, incrémenter ensemble schéma Python et Room, régénérer et vérifier `PokedexSchemaTest`.
Un ajout de lignes seul ne justifie pas une hausse artificielle du schéma.
Vérifier le mécanisme de remplacement de la base embarquée sur installation par-dessus.

Tester captures, favoris, formes, Zarbi, guides et observations d’errants par cartouche.
Si le suivi devient commun à Sinnoh/HGSS, lire encore `sinnohRoamers` des anciens JSON et définir
clairement le format écrit ; ne pas renommer une clé sans chemin de compatibilité.
Importer les anciens exports et refuser proprement versions, espèces ou formes invalides.
La progression GSC ne doit pas devenir automatiquement une progression HGSS.

## 5. Validation et définition de terminé

### Contrôles progressifs

- Tests ordinaires Python sans réseau ni cache ; fixtures minimales pour les nouveaux formats.
- Tests `pipeline` sur sources épinglées après préparation explicite, pas de réseau variable dans les tests.
- Tests JVM des règles, conversions, cas d’usage et ViewModels touchés, avec états vide et erreur.
- Régressions ciblées GSC, RF/VF et Sinnoh ; changement de famille et import/export historiques.
- Validation des références, taxonomies, rangs de Pokédex, formes et probabilités conditionnelles.
- Relecture de chaque lieu en planches, avec index des lieux et étages, pas seulement quelques exemples.
- Mesurer durée de génération, cache, taille des assets/APK et fluidité avec le catalogue final.
  Aucun seuil de performance inventé : comparer aux mesures existantes et justifier les écarts.

Commandes existantes à exécuter selon les fichiers touchés, depuis la racine :

```powershell
python tools/check_assets.py
python -m ruff check tools
python -m ruff format --check tools
Push-Location tools
python -m pytest -q
# Après préparation explicite des sources et modification des données :
python -m pytest -q -m pipeline
Pop-Location
.\gradlew.bat ktlintCheck checkNoGoogleServices lintDebug testDebugUnitTest assembleDebug
```

Les options de contrôle spécifiques à HGSS seront ajoutées et documentées avec les aperçus.
Ne pas appeler aujourd’hui une option HGSS proposée dans ce plan comme si elle existait déjà.
Chaque phase lance ses vérifications ciblées ; les contrôles complets sont obligatoires avant activation finale.
Relire le diff entier, vérifier 600 lignes/fichier source, 60 lignes/fonction et 120 caractères/ligne.

### Recette finale

Dans chaque version : départ à Bourg Geon, navigation Johto puis Kanto, intérieur/étage/pont,
rencontre filtrée puis fiche Pokémon puis retour carte, objet et offre, équipe et revanche,
Parc Safari conditionnel, radio, concours, fixe/errant, guide, succès et sauvegarde.
Vérifier hors ligne et avec animations désactivées, puis après changement vers chacun des groupes anciens.
Tester aussi l’absence de contenu et les erreurs de lecture, sans les assimiler.
Sur émulateur, conserver des captures ; sur téléphone, vérifier `adb devices` avant toute action.
Installer uniquement par-dessus avec `adb install -r -d`, sans effacement des données.
L’absence d’appareil se rapporte comme contrôle non exécuté ; elle ne constitue pas un test réussi.

HGSS n’entre dans `GAMES` qu’après couverture du périmètre, validation des deux cartouches,
relecture visuelle et contrôles complets verts. Versionner tous les assets finaux et `assets.sha256`,
jamais les caches, sources brutes, aperçus ou planches de session.
Actualiser README, index, documentation des sources et règles HGSS ; ajouter une note française
dans `RELEASE_NOTES.md` pour les changements visibles. Aucun commit ni publication automatique.

## 6. Risques et décisions à résoudre au bon moment

| Risque | Preuve ou décision exigée avant la suite |
|---|---|
| Ressource HGSS absente sans ROM | Inventaire au commit et lieu complet avant généralisation. |
| Lecteur DS à deux variantes | Sélection explicite HGSS et tests conservant les sorties DP/Pt. |
| Divergences entre cartouches | Comparaison des données et de la géométrie ; variantes jamais écrasées. |
| Parc Safari combinatoire | Modèle conditionnel borné avant génération de toutes les rencontres. |
| Valeurs contemporaines de PokéAPI | Comparaison aux données personnelles et au moteur HGSS. |
| Anciennes règles GSC réutilisées | Preuve HGSS par mécanique, notamment Balls, arbres et reproduction. |
| Guides français sur source américaine | Relecture des contenus régionaux et différences documentées. |
| Collision d’identifiants ou progression | Tests de catalogue, base mise à jour et sauvegardes anciennes. |
| Set de succès commun | Mapping explicite des deux versions et absence de doublons/perte de progression. |
| Sessions trop longues | Un livrable borné, prérequis et preuve de sortie pour chaque session ci-dessous. |

## 7. Liste de tâches par phases et sessions

Chaque case correspond à **une session IA ciblée**, éventuellement fractionnée si le diff devient trop large.
Une session reprend les fichiers et preuves de la précédente ; elle n’effectue pas toutes les phases à la fois.
En clôture, noter sous la case : fichiers modifiés, commande/aperçu produit, contrôles réellement exécutés,
questions résolues, éventuel blocage et prochaine action précise. Cocher uniquement après validation.
Conserver les artefacts volumineux dans `tools/build/scratchpad/` et les décisions durables dans la documentation.
Les phases avancent dans l’ordre ; aucune dépendance implicite à un cache de session perdu.

### Phase 0 — Qualifier les sources

- [x] **0A — Inventaire HGSS.** Lire le dépôt actuel, figer le commit candidat, relever variantes,
  ressources absentes, PokéAPI, licences et correspondances françaises. Sortie : matrice de provenance et blocages.
- [x] **0B — Contrats et périmètre.** Définir identifiants, régions, famille, catalogue des contenus,
  capacités et dépendances de génération ; décider le traitement des variantes régionales et du set de succès.
  Sortie : décisions documentées et jeux préparatoires isolés, sans activation Android.

Résultats : [qualification, provenance et blocages](docs/generations/sources-hgss.md),
[empreintes des sources](docs/generations/sources-hgss.json) et contrat `hgss_preparation.py`.
Le commit retenu est `6988158691eb6178cff697cda0428045ddcba5fb`. Le régional natif de 256 entrées
est identique aux CSV PokéAPI épinglés. Les jeux restent dans `PREPARATORY_GAMES`, hors de
`GAMES_IN_PROGRESS` : le pipeline générique ne sait pas encore lire HGSS et lancerait ses lecteurs Sinnoh.
Le transfert vers les jeux générables est conditionné à l'aiguillage explicite et à la preuve de phase 1.

### Phase 1 — Prouver les cartes avant de généraliser

- [x] **1A — Lecteur minimal.** Extraire Bourg Geon et son intérieur dans les deux versions,
  avec fixtures et erreurs de format explicites. Sortie : données natives, unités et références contrôlées.
- [x] **1B — Rendu complet minimal.** Produire tuiles, collision, passage aller/retour et acteur,
  puis un lieu à plusieurs niveaux. Sortie : preuve visuelle et génération reproductible sans ROM.
  **Arrêt de cette branche si la preuve échoue ; aucune substitution GSC.**

Résultats : [preuve cartographique et formats HGSS](docs/generations/cartes-hgss.md),
[empreintes d'entrée](docs/generations/cartes-hgss-sources.json) et
[preuve synthétique](docs/generations/cartes-hgss-preuve.json).
Lecteurs `pret_hgss_binary.py`/`pret_hgss_maps.py`, rendu `maps_render_hgss.py`, validation
`validate_hgss_maps.py`, aperçu `preview_maps_hgss.py`, option explicite dans `tools/build_data.py`,
fixtures et recette dans `test_hgss_maps.py`/`test_hgss_map_sources.py`.
Les codecs de triangles Nitro, de pose NSBTX et d'éclairage sont réutilisés sans modifier leurs règles ;
les tests existants suivent leurs nouveaux noms publics. README, index et documentation sont actualisés.

`python tools/build_data.py --hgss-maps-only` produit `tools/build/preview/hgss-maps/` pour les deux versions :
Bourg Geon, laboratoire RDC/étage, Routes 29 et 47. Deux allers-retours sont contrôlés, sept paires de cases
franchissent la frontière Route 29/Bourg Geon et 118 cases de la Route 47 ont plusieurs surfaces.
La planche `tools/build/scratchpad/hgss-phase1-review.png` et la coupe inférieure ont été relues.
Une seconde génération avec `--preview tools/build/scratchpad/hgss-repro` reproduit exactement les
361 fichiers de l'inventaire, soit 8 799 306 octets ; durées de 72,82 et 97,14 secondes, sans cache de rendu persistant.

Contrôles exécutés : `python tools/check_assets.py`, Ruff et son contrôle de format sur `tools`,
`python -m pytest -q` (951 réussis), puis tests `pipeline` ciblant `test_hgss_preparation.py`,
`test_hgss_map_sources.py`, `test_gen4_map_sources.py` et `test_gen4_render_sources.py` (18 réussis).
La dernière recette ciblée, incluant fixtures, tailles de fonctions et sources, passe ses 50 tests.
Les limites de fichiers/fonctions/lignes et `git diff --check` passent.
Les contrôles Android et la suite `pipeline` intégrale ne sont pas lancés : aucun asset distribué,
schéma ni code Android ne change ; la recette de cette phase porte sur l'aperçu isolé et les codecs DS concernés.

Incidents résolus : accès aux dossiers temporaires refusé par le bac à sable Windows, génération/tests
relancés avec autorisation ; entrée standard Git explicitement détachée sous pytest ; imports des codecs
renommés, collision de nom méthode/cache et dépassement de 60 lignes corrigés.
Une attente de test initialement fausse a été rectifiée :
la case témoin de la Route 47 porte l'attribut natif `0x15`, pas zéro. Aucun échec de contrôle restant.
La preuve sans ROM réussit ; aucun remplacement GSC/Sinnoh et aucune activation HGSS.
La preuve autorise les données Pokémon indépendantes ; la généralisation Johto/Kanto reste en phase 3.

### Phase 2 — Données Pokémon indépendantes des cartes complètes

- [x] **2A — Pokémon et Pokédex.** Préparer `--hgss-pokemon-only`, contrôler régional/National,
  données personnelles, talents, attaques et CT/CS. Sortie : aperçu validé et comparaisons de sources.
- [x] **2B — Formes et évolutions.** Traiter formes, sprites, Zarbi, tuteurs et obtentions par échange/transfert.
  Sortie : tests par cartouche et aucun remplacement par les valeurs GSC ou les valeurs modernes.

Résultats : [catalogue et recette Pokémon HGSS](docs/generations/pokemon-hgss.md),
[empreintes des sources](docs/generations/pokemon-hgss-sources.json), lecteurs `pret_hgss_pokemon.py`,
assemblage `catalog_pokemon_hgss.py`, comparaison `compare_pokemon_hgss.py`, formes `pokemon_forms_hgss.py`,
conditions `evolution_hgss.py` et aperçu `preview_pokemon_hgss.py`.
Les corrections françaises restent dans `tools/data/hgss_pokemon_forms.csv` et `hgss_pokemon_rules.json`.

`python tools/build_data.py --hgss-pokemon-only` produit un catalogue JSON autonome et les sprites dans
`tools/build/preview/hgss-pokemon/`, sans carte, base SQL artificielle ni activation Android.
Les 493 espèces, 256 rangs régionaux, 467 attaques, 92 CT et huit CS sont contrôlés.
Les statistiques historiques, types, talents, attaques par niveau, machines et tuteurs de la table principale
concordent avec PokéAPI. Cinq différences de taux de capture non historisés sont expliquées et gardent
la valeur HGSS ; les méthodes complémentaires d'apprentissage gardent explicitement leur provenance PokéAPI groupe 10.
Les chaînes d'évolution concordent ; les évolutions exigeant Sinnoh restent distinctes des échanges ordinaires.

Les 47 formes nommées de chaque cartouche ont leurs profils natifs, niveaux, tuteurs et sprites ;
les 28 Zarbi gardent leurs groupes de déblocage vérifiés dans le moteur. Pichu Troizépi est traité séparément :
il ne peut ni évoluer ni être échangé, et sa planche HGSS est conservée sans inventer de variante Noir/Blanc.
Les règles d'accès des autres formes conservent leurs références aux scripts et aux objets.

Deux générations indépendantes reproduisent exactement les 2 264 fichiers inventoriés, soit
45 870 203 octets avec l'inventaire ; durées de 11,20 et 10,79 secondes.
Le remplacement n'intervient qu'après validation et restaure l'ancien aperçu si le renommage échoue.

Contrôles exécutés : `python tools/check_assets.py`, Ruff et format sur tout `tools`,
`python -m pytest -q` (968 réussis), puis tests `pipeline` HGSS Pokémon et qualification
(14 réussis). Limites 600/60 lignes et `git diff --check` vérifiées.
Les contrôles Android et la suite `pipeline` intégrale ne sont pas lancés : aucun asset distribué,
schéma ou code Android n'a changé ; les sources concernées sont couvertes par la recette ciblée.

Incidents résolus : accès aux dossiers temporaires/cache pytest refusé dans le bac à sable Windows,
relance autorisée ; formats techniques NARC et alias `ITEM_UPGRADE` ajustés aux sources.
Une attente de test erronée a été corrigée : Cheniselle Sable apprend Telluriforce par tuteur,
mais pas Coup d'Boule. Le contrôle Ruff a été relancé depuis le bon dossier après un chemin vide.
Aucun échec de contrôle restant. Prochaine action : phase 3, catalogue complet Johto/Kanto.

### Phase 3 — Cartes complètes et navigation

- [x] **3A — Johto.** Étendre l’aperçu de cartes à ses extérieurs, intérieurs et donjons,
  nommer et assembler les plans. Sortie : catalogue Johto sans référence cassée et planches relues.
- [x] **3B — Kanto.** Traiter ses cartes remaniées, accès, plans et transitions interrégionales.
  Sortie : catalogue Kanto complet dans les deux versions.
- [x] **3C — Lieux spéciaux et étages.** Finaliser installations, niveaux superposés,
  décors dynamiques et liaisons scriptées. Sortie : couverture visuelle de tout le catalogue et inventaire.

**Bilan 3A — 22 octobre 2026.** Le [catalogue Johto](docs/generations/cartes-hgss.md) couvre
246 lieux nommés en français, réunis en 110 plans, avec 684 passages et 80 voisinages de matrice.
Les 540 en-têtes sont classés dans `hgss_maps.csv`, sans utiliser les coordonnées ou cartes GSC.
Le Casino de Doublonville reste rattaché à Johto malgré son indicateur natif Kanto.
Les destinations fixes et leurs ancres sont vérifiées ; 16 frontières hors périmètre et trois sorties
d'ascenseur mémorisées sont explicites. Les repères gardent leurs surfaces BDHC et leurs translations.

`python tools/build_data.py --hgss-maps-only --map-workers 4` conserve la preuve initiale et produit
le catalogue dans `tools/build/preview/hgss-maps/johto/`. Les 795 empreintes d'entrée, les corrections
de textures et de hauteur d'escalier, ainsi que les rendus bornés et leur cache sont contrôlés.
La sortie compte 8 741 fichiers, 64 441 388 octets ; génération avec cache en 179,95 secondes.
Les 24 planches de `review_hgss_maps.py` ont été relues : 357 vues, avec un détail des extérieurs.
La [preuve versionnée](docs/generations/cartes-hgss-johto-preuve.json) garde leurs empreintes et celles
des 246 images ; le réexport des libellés conserve exactement les pixels des cartes.

Contrôles exécutés : assets distribués et aperçu via `check_assets.py --hgss-maps`, Ruff et format
sur tout `tools`, suite ordinaire (990 réussis), puis contrôles ciblés finaux (23 réussis, dont
la nouvelle vérification de couverture de la preuve) et suite `pipeline` intégrale (410 réussis).
Limites 600/60 lignes et diff relus. Aucun contrôle en échec restant.
Les contrôles Android et ADB ne sont pas lancés : aucun code Android ni asset distribué n'a changé.
Incidents corrigés : permissions Windows des dossiers temporaires, encodage des libellés,
cadres trop grands, double échelle des modèles articulés, casse des étages et masque des miniatures.
Les jeux restent préparatoires ; les compléments de 3B et 3C sont décrits ci-dessous.

**Bilan 3B et 3C — 22 octobre 2026.** L'[atlas intégral](docs/generations/cartes-hgss-atlas.md)
couvre les deux versions : 192 cartes de Kanto et 58 lieux spéciaux ou gabarits complètent Johto,
soit 496 entrées, 224 plans, 196 coupes et une surface non visuelle explicitement inventoriée.
Les 1 314 portes, 164 voisinages de blocs et 181 instructions de déplacement conservent leurs références ;
train, Aquaria, destinations mémorisées et portes déplacées par le scénario restent distincts.
Les douze décors ajoutés par les mécanismes d'arènes sont placés dans leur état initial.
Le Safari conserve ses douze habitats, deux gabarits supplémentaires, six emplacements et dix configurations
initiales, sans imposer un arrangement universel. Les 60 planches relues et les empreintes des images sont
conservées dans la [preuve](docs/generations/cartes-hgss-atlas-preuve.json).
Les contrôles des assets et les dix tests de recette HGSS passent ; Ruff et les tests Python ordinaires
couvrent aussi les nouvelles règles. Aucun build Android n'est nécessaire pour cet aperçu isolé.
Incidents corrigés : droits des dossiers temporaires Windows, encodage, références de textures,
projection Nitro, deux constantes natives mal nommées, titre du plan Kanto et une surface BDHC sans géométrie visible.

### Phase 4 — Rencontres, en lots maîtrisés

- [x] **4A — Tables ordinaires.** Marche, eau, pêche, horaires et taux issus du moteur ;
  ajouter l’aperçu de rencontres et le rapport comparatif PokéAPI. Sortie : distributions cohérentes et écarts classés.
- [x] **4B — Remplacements et méthodes.** Radio, essaims, arbres et rochers ; taxonomie et filtres associés.
  Sortie : tests des conditions combinées et incompatibles, traductions françaises.
- [x] **4C — Concours et Safari.** Modéliser jours, National, blocs et délais avec limites de calcul.
  Sortie : configurations vérifiables et présentation de taux conditionnels sans prédiction.
- [x] **4D — Obtentions particulières.** Fixes, errants, dons, œufs, échanges, Pokéwalker et événements.
  Sortie : provenance et exclusions des objectifs ordinaires validées.
- [x] **4E — Placement.** Adapter l’éditeur aux terrains HGSS et relire les points des deux régions.
  Sortie : `map_spots.csv` validé, aucun point hors terrain ou lieu dépourvu de couverture sans explication.

**Bilan 4A et 4B — 22 octobre 2026.** L’[aperçu des rencontres](docs/generations/rencontres-hgss.md),
généré par `--hgss-encounters-only`, conserve 142 banques, leurs en-têtes et 14 616 distributions compatibles
dans les deux versions. Les 252 tables d’arbres couvrent 60 lieux, avec leurs groupes de coordonnées,
catégories et tables de décision selon l’identifiant du dresseur. Les horaires de pêche, remplacements
radio/essaim et poids Éclate-Roc suivent le moteur ; les taux de déclenchement restent séparés des taux d’espèce.
La comparaison donne 14 256 distributions identiques, 360 écarts 90/10 contre 80/20 pour Éclate-Roc,
et huit tables PokéAPI du quai de Carmin absentes du moteur. Tout autre écart ordinaire est bloquant.
Les identifiants techniques inutilisés 90/142 et les exclusions Safari, concours, obtentions particulières
et catégories d’arbres absentes de PokéAPI sont explicites. Les filtres Python/Kotlin, les exigences françaises
de la radio et les incompatibilités sont couverts ; les remakes restent isolés des jeux Android distribués.
La [preuve versionnée](docs/generations/rencontres-hgss-preuve.json) conserve les sources et empreintes des sorties.
Les coordonnées natives des arbres n’anticipent pas la projection et la curation de 4E.

Contrôles réussis : génération finale (15,00 s), assets distribués et aperçu, Ruff et format sur tout `tools`,
1 036 tests Python ordinaires, 415 tests des sources (17 min 33 s), puis 34 tests ciblés sur l’état final,
dont la reproduction des empreintes du catalogue et du rapport. Android : ktlint, absence de services Google,
Lint, tests JVM/Compose et APK debug réussis. Limites 600/60 lignes et diff relus ; aucun test sur téléphone.
La dépréciation AGP déjà décrite dans `docs/developpement.md` reste visible, sans nouvelle suppression.
Incidents corrigés : permissions Windows des aperçus/caches, lecture JSON limitée à 4 Mio pour une sortie
de 17,8 Mo, variantes de noms des banques techniques et attente de test initialement fixée à 70 lieux d’arbres
au lieu des 60 comptés dans la source. Le quai de Carmin et la condition « hors concours » sont classés explicitement.

**Bilan 4E — 22 octobre 2026.** L'éditeur ouvre `hgss-placement/` sans base Android artificielle,
avec régions, deux cartouches, terrains natifs, centres projetés et passages. Le nouvel aperçu se génère
avec `python tools/build_data.py --hgss-placement-only` ; les treize planches de relecture viennent de
`python tools/review_hgss_spots.py`. Les 151 lieux audités couvrent Johto, Kanto et les gabarits Safari.
`map_spots.csv` conserve 5 655 points, validés sur 296 terrains : 268 couverts et 28 absences expliquées dans
`hgss_spot_exclusions.csv`. Aucun point hors terrain ni absence sans explication ; 37 avertissements de
capacité restent visibles et documentés. Les rencontres sans marqueur restent dans les listes.
La [preuve versionnée](docs/generations/placements-hgss-preuve.json) conserve les comptes et empreintes.

Contrôles : aperçu final, assets distribués, Ruff et format complets, limites 600/60 et diff réussis.
1 070 tests Python ordinaires réussis. La suite des sources a donné 416 succès et un échec HGSS pendant
le recalcul des données ; le test natif HGSS relancé explicitement sur l'état figé réussit (65,71 s).
Une relance globale a été interrompue au profit de cette relance ciblée. L'éditeur Tk a été ouvert sans
fenêtre visible : zéro erreur ; les treize planches finales ont été relues. Aucun contrôle Android ni ADB
relancé : outils et données préparatoires uniquement, sans modification des assets distribués.

Incidents traités : accès Windows aux aperçus et caches temporaires, lecteur JSON natif limité à 4 Mio
remplacé par une lecture préparatoire bornée à 64 Mio, commande Ruff appelée par `python -m ruff`.
L'attente du test de base supposait à tort toutes les familles du CSV déjà déclarées pour l'application ;
elle inclut maintenant les contrats préparatoires, contrôlés séparément sans activation HGSS.
La relecture a retiré les projections transparentes/noires, flottantes ou masquées et les points aquatiques
sur le décor ; les hauteurs d'eau restent des candidats relus visuellement, sans hauteur arbitraire.

### Phase 5 — Personnages, objets et services

- [ ] **5A — Acteurs et combats.** Lire sprites, scripts, équipes et variables de starter/scénario.
  Sortie : aperçu de personnages, placements relus et liens acteur/combat/lieu corrects.
- [ ] **5B — Revanches et calendrier.** Extraire Pokématos, champions et Ligue selon conditions.
  Sortie : rendez-vous et équipes alternatives vérifiés sans héritage du Cherche VS.
- [ ] **5C — Objets et offres.** Objets cachés/visibles, boutiques, Noigrumes, tuteurs, échanges et récompenses.
  Sortie : quantités, coûts, délais et étapes testés, compléments éditoriaux tracés.

### Phase 6 — Règles Android et compatibilité

- [ ] **6A — Identité et capacités.** Déclarer versions/groupe, choix des jeux, jaquettes et régions ;
  compléter tous les choix exhaustifs. Sortie : application testable avec le catalogue préparatoire,
  jeux non distribués.
- [ ] **6B — Capture.** Ajouter le contexte HGSS, Balls et environnements avec tests de frontières.
  Sortie : règles moteur prouvées et aucune régression GSC/Sinnoh.
- [ ] **6C — Reproduction et bonheur.** Implémenter les différences prouvées et leurs outils français.
  Sortie : matrice des règles couverte par les tests du domaine et des cas d’usage.
- [ ] **6D — Base et sauvegardes.** Finaliser export commun, éventuel schéma, collections et errants.
  Sortie : schéma aligné, mise à jour de base et imports historiques testés sans perte de progression.

### Phase 7 — Guides et activités des remakes

- [ ] **7A — Soluce Johto.** Guides par version, quêtes, lieux/PNJ/objets liés et étapes stables.
  Sortie : parcours principal relu en français.
- [ ] **7B — Kanto et après-jeu.** Soluce jusqu’à Red, objectifs de capture et calendrier.
  Sortie : objectifs calculés par cartouche avec exclusions explicites.
- [ ] **7C — Catalogues particuliers.** Pokéathlon, Noigrumes, Safari, Pokéwalker et autres activités recensées.
  Sortie : données structurées et guides vérifiés ; fractionner par activité si nécessaire.
- [ ] **7D — Zone de Combat.** Comparer Platine et HGSS, importer seulement les données prouvées communes.
  Sortie : installations, équipes possibles, conditions et récompenses correctes, sans simulation des tirages.
- [ ] **7E — Succès.** Relire/traduire les archives existantes, générer les ressources et tester
  le set partagé ainsi que la synchronisation manuelle. Sortie : consultation complète hors ligne.

### Phase 8 — Activation, recette et livraison

- [ ] **8A — Génération candidate.** Produire tous les assets HGSS, contrôler reproductibilité,
  inventaires et non-régression des jeux existants. Sortie : base, cartes et catalogues cohérents prêts à activer.
- [ ] **8B — Activation contrôlée.** Passer HGSS de `GAMES_IN_PROGRESS` à `GAMES`, actualiser
  documentation et notes, puis lancer tous les contrôles Python/Android. Sortie : contrôles complets verts.
- [ ] **8C — Recette finale.** Exécuter les parcours des deux cartouches, sauvegardes et changements de jeu,
  mesurer taille/fluidité et vérifier l’installation par-dessus si un appareil est disponible.
  Sortie : rapport honnête des résultats et limites matérielles, captures et aucun défaut connu laissé volontairement.
- [ ] **8D — Clôture.** Relire le diff et les assets versionnés, vérifier les limites de code,
  récapituler les preuves et proposer un message de commit français. Commit et publication sur demande explicite.

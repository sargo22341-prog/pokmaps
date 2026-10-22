# Rencontres préparatoires HeartGold et SoulSilver

Lots 4A à 4D du [plan](../../plan4g%20remake.md), sans activation des remakes dans l’application.
Le moteur et les tables proviennent du commit HGSS fixé dans `sources.HGSS_PRET_COMMIT` ;
les CSV de comparaison proviennent de `sources.POKEAPI_COMMIT`.
L’[inventaire des sources](rencontres-hgss-sources.json) fixe leurs empreintes ;
la [preuve de génération](rencontres-hgss-preuve.json) conserve les comptes et empreintes des sorties.

## Générer et vérifier

Après l’aperçu cartographique complet validé :

```powershell
python tools/build_data.py --hgss-encounters-only
python tools/check_assets.py --hgss-encounters tools/build/preview/hgss-encounters
cd tools
python -m pytest -q tests/test_hgss_wild.py
python -m pytest -q -m pipeline tests/test_hgss_wild_sources.py
```

La commande vérifie les sources et les cartes existantes, puis remplace `tools/build/preview/hgss-encounters/`
après validation du staging. Un échec conserve l’ancien aperçu. Aucun rendu cartographique, téléchargement
de ROM ni génération des assets Android n’est nécessaire. Les cartes périmées doivent être régénérées
avec `--hgss-maps-only` ; leurs données ne sont jamais remplacées par celles de GSC ou de Sinnoh.

| Sortie | Contenu |
|---|---|
| `encounters.json` | Méthodes et conditions françaises, espèces, lieux, banques, distributions et arbres natifs. |
| `comparison.json` | Distributions comparées, écarts classés, données PokéAPI seules et exclusions motivées. |
| `sources.json` | Commits, empreintes natives/PokéAPI, inventaire des cartes et recette Python/éditoriale. |
| `summary.json`, `inventory.json` | Comptes et intégrité des sorties. |

Les 142 banques sont indexées à partir de zéro ; leurs correspondances PokéAPI utilisent `game_index = banque + 1`.
Chaque banque garde tous ses en-têtes natifs : plusieurs cartes peuvent partager une table.
Les sept banques sans en-tête restent explicitement identifiées, sans lieu artificiel.
L’index natif déclare aussi `ENCDATA_UNUSED_142` sans membre JSON ; `090` désigne `ENCDATA_UNUSED_090`.
Les arbres sont indexés par en-tête, indépendamment des banques ordinaires.

## Distributions et conditions

Les taux sont lus dans les tables ; les poids des emplacements suivent `src/field/encounter_check.c` :

| Méthode | Poids dans l’ordre natif |
|---|---|
| Marche | 20, 20, 10, 10, 10, 10, 5, 5, 4, 4, 1, 1 |
| Surf | 60, 30, 5, 4, 1 |
| Chaque canne | 40, 30, 15, 10, 5 |
| Éclate-Roc | 80, 20 |
| Coup d’Boule, par catégorie d’arbre | 50, 15, 15, 10, 5, 5 |

Chaque distribution conditionnelle totalise 100 %. `rate` conserve le paramètre brut de déclenchement
du moteur, séparé de la probabilité d’espèce : ce n’est pas un taux de rencontre par pas.
Les talents, objets tenus, répulsifs et errants ne sont pas inclus dans ces distributions.
Marche Pokémon et Berceuse Pokémon gardent les espèces ordinaires : le catalogue documente leur
modificateur respectif de +25 et −25 sur le premier seuil du moteur (octet non signé, avant plafond à 100),
ainsi que leur calendrier. Ce seuil dépend aussi du déplacement, du terrain et des pas précédents ;
il n’est pas confondu avec `rate` et aucune probabilité par pas n’est simulée.
Les arbres conservent `rate: null` : aucune probabilité universelle par arbre n’est fabriquée.

Les variantes HG/SS d’espèces et de niveaux sont résolues avant les remplacements.
Matin, jour (soir inclus) et nuit (fin de nuit incluse) sont distincts.
L’essaim ne modifie que les vingt lieux/méthodes de `sSwarmMapLUT` ; ses espèces ne sont pas inventées
dans les autres lieux à partir de champs inutilisés des tables.

- Marche : essaim sur les emplacements 0 et 1, puis radio sur 2 à 5.
- Surf : essaim sur l’emplacement 0 seulement.
- Pêche nocturne : emplacement 3 de la Super Canne et 1 de la Méga Canne.
  L’essaim vient ensuite : emplacement 2 de la Canne, 0/2/3 de la Super Canne, tous ceux de la Méga Canne.
- Son de Hoenn : mercredi avec le National ; Son de Sinnoh : jeudi avec le National.
  Les deux radios sont exclusives. Essaim et radio peuvent se combiner.
  Le script du quai d’Oliville lie le déblocage des essaims à celui du National.

Le calcul est borné à 18 configurations représentatives par méthode et banque : trois horaires,
trois choix radio et deux états d’essaim. Les jours sans effet ne sont pas multipliés.
`filter_distributions` sélectionne une version, une méthode et une configuration compatible.
Les filtres Android reconnaissent les trois catégories d’arbres, Éclate-Roc et une radio exclusive,
avec les exigences françaises affichées ; aucun jeu HGSS n’est encore déclaré dans Android.

Les 60 lieux d’arbres conservent groupes de coordonnées et tables communes/rares/particulières.
`src/field/headbutt.c` choisit la catégorie ordinaire selon le dernier chiffre de l’identifiant complet
du dresseur et le groupe d’arbre ; à partir de cinq groupes, l’index est pris modulo cinq.
Les cinq tables de décision et l’état « aucun combat » sont conservés, sans prédire l’identifiant du joueur.
Les coordonnées restent natives : leur projection et leur curation appartiennent au lot 4E.

## Comparaison et périmètre

14 256 distributions correspondent exactement à PokéAPI, en conservant chaque plage de niveaux.
Les 360 différences sont les mêmes vingt tables Éclate-Roc (dix lieux, deux versions),
répétées dans les 18 configurations : PokéAPI fournit 90/10, le moteur utilise 80/20.
Le validateur accepte uniquement cette transformation dans le même ordre ; tout autre écart arrête la génération.

Huit tables supplémentaires de PokéAPI concernent le quai de Carmin (`location_area_id = 349`,
Surf et trois cannes, deux versions). Les en-têtes HGSS 386 et 387 déclarent `ENCDATA_NA` :
elles sont classées `table_absente_moteur`, avec les lignes PokéAPI conservées et aucune rencontre native ajoutée.

Les tables d’arbres PokéAPI ne distinguent pas les catégories natives : leur exclusion de la comparaison
numérique est explicite, et les trois distributions du moteur restent séparées.
Le Safari et le concours restent hors comparaison PokéAPI ordinaire ; leurs tables natives sont validées séparément.
Fixes, errants, dons, échanges et événements ont leur inventaire de provenance distinct des distributions.
La comparaison du Parc Naturel sélectionne explicitement « hors concours ».

## Concours et Safari — 4C

`special_wild` conserve les six configurations du concours : mardi, jeudi et samedi, avant et après le National.
Les jours sont ISO (lundi = 0), convertis explicitement depuis le calendrier DS (dimanche = 0).
Avant le National, les trois jours emploient la même table ; après, chacun sélectionne sa propre table.
Les seuils cumulés de `mushi_encount.csv` deviennent des poids : 20, 20, 10, 10, 10, 10, 5, 5, 5, 5.
Le taux reste conditionnel à une rencontre pendant le concours, sans prédiction du classement ni de la capture.

Les douze habitats Safari gardent cinq méthodes, trois horaires, les dix emplacements ordinaires et les candidats
supplémentaires dans l'ordre natif. `SafariConfiguration` valide quatre nombres de blocs et les objets décoratifs,
avec trente objets au total. Les blocs et la maturation requièrent le National et le déblocage déclaré des objets.
L'âge enregistré de l'habitat est compris entre 0 et 255 jours ; il ne désigne pas l'âge de chaque objet.
Les multiplicateurs suivent `getObjectLevelBoost` dans `src/unk_02097268.c` :

| Type | Seuils en jours enregistrés pour les multiplicateurs 2 à 7 |
|---|---|
| Plaine | 10, 50, 100, 150, 200, 250 |
| Forêt | 20, 60, 110, 160, 210, 250 |
| Pic | 30, 70, 120, 170, 220, 250 |
| Eau | 40, 80, 130, 180, 230, 250 |

`safari_slots` vérifie simultanément les deux exigences lorsqu'elles existent. Les dix premiers candidats
admissibles remplacent les premiers emplacements, dans l'ordre de la table ; les suivants n'ajoutent aucun taux.
Chaque emplacement vaut 10 %, sans talent, répulsif ni effet de niveau du meneur. Sans configuration, le catalogue
présente les exigences, sans probabilité globale d'espèce. Il ne calcule aucune date réelle de déblocage.
Une évaluation inspecte au plus trente candidats, deux exigences chacun et dix emplacements : aucune énumération
des arrangements ni des combinaisons de jours/blocs. Six habitats peuvent être actifs parmi les douze ;
les configurations cartographiques initiales restent dans l'aperçu des cartes.

## Obtentions particulières — 4D

`obtainings` inventorie 62 occurrences de commandes dans les scripts, avec fichier, ligne, label, arguments
et branches natives conservées. Ce compte inclut des réapparitions et des occurrences techniques ; ce n'est pas
un nombre de cadeaux uniques. Les candidats d'espèce des arguments variables restent des alternatives,
jamais une affirmation que tous ces Pokémon sont accessibles ensemble ou dans les deux versions.
Les quatre errants, les fixes, les dons, les œufs de Primo et de Togepi, les starters, les fossiles et les
récompenses du Casino restent séparés des tables aléatoires. Les treize membres de l'archive native des échanges
gardent espèce reçue, contrepartie et les deux prêts (Caratroc et Piafabec).

L'éligibilité `ordinary_objective` porte sur la provenance, sous conditions, pas sur l'espèce entière.
Pichu Troizépi, les dons des Ruines Sinjoh et les Lati du Mystécristal sont exclus par événement externe ;
Rayquaza est exclu par son besoin de Pokémon issus de deux cartouches HGSS. Les parcours Pokéwalker ont la
catégorie accessoire, distincte des distributions et des transferts, et aucun en-tête cartographique artificiel.
Les 27 identifiants de parcours sont inventoriés ; leur catalogue détaillé de récompenses relève du lot 7C.
Les distributions n'impliquent aucune disponibilité actuelle et ne créent pas de capture locale de Celebi ou d'Arceus.
Une autre provenance locale de la même espèce reste éligible, notamment le Lati errant de la cartouche.
Le calcul des objectifs compatibles avec les choix de starters et de fossiles reste celui du lot 7B.

Le [catalogue particulier versionné](rencontres-hgss-particulieres.json) permet de vérifier ces données sans cache.
Son empreinte figure dans la preuve de génération ; les tests pipeline reconstruisent aussi le catalogue complet
depuis les sources épinglées. L'affichage Android et la traduction des branches de scénario appartiennent aux
lots d'intégration des personnages et d'activation ; les remakes ne sont pas encore sélectionnables.

## Placement — 4E

`python tools/build_data.py --hgss-placement-only` valide les aperçus des cartes et des rencontres,
les sources natives et les retouches de `tools/data/map_spots.csv`, puis écrit `hgss-placement/`.
Cette étape ne télécharge rien, n'active pas les remakes et ne modifie pas les assets Android.
Un échec préserve le dernier aperçu valide. La génération ne réécrit jamais les points éditoriaux.

```powershell
python tools/map_editor.py --assets tools/build/preview/hgss-placement
python tools/review_hgss_spots.py
```

L'éditeur lit le catalogue préparatoire directement, sans base SQLite artificielle. Les listes gardent
les espèces des deux versions et de toutes les configurations ; « — » évite d'additionner leurs probabilités
incompatibles. Le clic utilise les centres projetés HGSS, à douze pixels au plus, et les passages gardent
leur projection native. Les sprites de prévisualisation sont ceux déjà distribués par l'application.

Les comportements et leurs drapeaux viennent de `src/metatile_behavior.c` et de son enum natif :
herbes et sols de marche sans collision, eau surfable pour la pêche, eau à rencontre pour Surf.
Les arbres viennent des groupes réguliers et particuliers de `headbutt.json`, sans prédiction de leur
classement selon le dresseur ; les rochers sont les acteurs `SPRITE_BREAKROCK` des événements natifs.
Les cases des autres acteurs et des passages sont retirées du placement ordinaire.
Les hauteurs BDHC, altitudes de matrice et caméras HGSS projettent chaque centre dans le repère de l'image.
Les surfaces superposées, hauteurs absentes, projections hors image, pixels transparents et surfaces
techniques noires opaques sont écartés. Pour la marche, une seconde vérification compare la profondeur
BDHC à celle du décor opaque, avec les mêmes triangles, textures et faces que le rasteriseur des cartes.
Une demi-case de tolérance (huit unités de profondeur) accepte le faible décalage des sols visuels,
notamment 4,23 unités dans les gabarits Safari, sans accepter une surface derrière une falaise.
Les arbres et rochers restent attachés à leur objet, sans être rejetés parce que leur propre modèle cache le sol.
Pour l'eau, la surface haute reste candidate même si le BDHC contient aussi un fond ; les plans d'eau visuels
ne suivent pas toujours ces surfaces. La curation retient uniquement les points relus sur l'eau bleue/cyan
de l'image, sans imposer une équivalence avec le sol opaque ni placer de Pokémon sur les props ou les berges.
L'aperçu conserve les candidats rejetés et leurs deux profondeurs pour la relecture.

La curation retient **5 655 points**, pour **151 lieux audités** : 81 à Johto, 57 à Kanto et 13 gabarits/lieux spéciaux.
Les 296 terrains contrôlés comprennent 268 terrains avec points et **28 absences expliquées**.
Les points sont espacés d'au moins 32 pixels dans chaque terrain ; les propositions initiales sont
déterministes et plafonnées à quarante points, puis restent des retouches éditoriales.
Les treize planches couvrent tous les lieux ; les images détaillées et leur index restent dans
`tools/build/scratchpad/hgss-placement-review/`. Vert : herbes ; orange : sol ; bleu : eau ; violet : arbres ; rouge : rochers.

`tools/data/hgss_spot_exclusions.csv` explique chaque terrain sans point : sept habitats Safari sans eau malgré
leurs tables, l'en-tête Safari dynamique 357 pour la marche et l'eau, cinq salles/étages sans eau malgré leur banque,
et les dix-sept cases libres de la salle de Lugia sans surface BDHC exploitable.
Trois autres terrains ne passent pas le rapprochement BDHC/décor : marche au deuxième étage de la Tour Chétiflor,
au neuvième étage de la Tour Carillon et au premier sous-sol du Puits Ramoloss.
Leurs espèces restent dans les listes, sans point flottant ou masqué ajouté pour remplir la carte.
La relecture aquatique écarte aussi dix terrains dont les candidats natifs projetables ne rejoignent pas
l'eau visible : Routes 6, 22, 30 et 43, Bourg Palette, Jadielle, Céladopole, Puits Ramoloss sous-sol 1,
et les deux états du square du Mont Sélénite. Le CSV d'exclusions conserve leurs comptes de candidats.
Le Safari se place sur ses douze gabarits, jamais sur un arrangement universel inventé de ses six habitats actifs.
Les rencontres de la salle de Lugia restent dans la liste ; aucune hauteur arbitraire ne crée de marqueur.
Tout terrain sans couverture ni raison, point hors terrain, carte inconnue ou exception inutilisée est bloquant.

L'éditeur conserve 37 avertissements de capacité : ces terrains ont des points, mais moins que l'union
des espèces et méthodes possibles. Une partie des Pokémon reste visible dans la liste du lieu.
Ces avertissements ne désignent pas un lieu sans couverture et ne changent aucune probabilité de rencontre.

La [preuve de couverture](placements-hgss-preuve.json) conserve les comptes, empreintes des points par terrain,
exclusions et prérequis. Le [contrat des terrains](placements-hgss-sources.json) épingle les lectures supplémentaires.
Les tests ordinaires vérifient les points versionnés sans cache ; le test pipeline reconstruit les terrains des
151 lieux depuis les sources épinglées et contrôle aussi les pixels sous les candidats.

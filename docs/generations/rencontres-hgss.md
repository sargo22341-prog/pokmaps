# Rencontres préparatoires HeartGold et SoulSilver

Lots 4A et 4B du [plan](../../plan4g%20remake.md), sans activation des remakes dans l’application.
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
Le Safari est recensé hors comparaison ; ses blocs et délais relèvent de 4C, comme les variantes de concours.
Fixes, errants, dons, échanges et événements sont classés hors de ce lot (4D).
La comparaison du Parc Naturel sélectionne explicitement « hors concours ».

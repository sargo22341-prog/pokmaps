# Preuve des cartes HeartGold et SoulSilver

Le prototype de phase 1 lit et rend cinq lieux depuis `pret/pokeheartgold` au commit
`6988158691eb6178cff697cda0428045ddcba5fb`, sans ROM et sans compiler le jeu.
Il reste séparé des cartes distribuées et ne rend pas HGSS disponible dans Android.

## Reproduire

Préparer les [sources qualifiées](sources-hgss.md#source-retenue-et-preuve-reproductible), puis lancer depuis la racine :

```powershell
python tools/build_data.py --hgss-maps-only
cd tools
python -m pytest -q tests/test_hgss_preparation.py tests/test_hgss_map_sources.py -m pipeline
```

La commande lit `--cache/hgss-qualification` ; elle ne télécharge rien et ne reconstruit pas Sinnoh.
Le commit Git et toutes les [empreintes d'entrée](cartes-hgss-sources.json) sont contrôlés avant le rendu.
`--preview` choisit le parent du dossier `hgss-maps/`. Les sources et assets distribués ne peuvent pas
servir de destination. Le remplacement intervient après validation des deux versions ; un échec de
lecture ou de rendu conserve l'aperçu précédent. Les fichiers d'aperçu restent hors Git.

Chaque version contient un dossier par lieu, avec `native.json`, `map.png`, `review.png`, `collision.png`
et la pyramide WebP `tiles/`. La Route 47 ajoute `lower.png` et `lower-tiles/`.
`proof.json` conserve unités, sources, empreintes des pixels, acteurs témoins et liaisons contrôlées.
`inventory.json` couvre tous les fichiers produits. Ce lot de preuve n'est pas encore le catalogue
complet destiné à l'éditeur de rencontres ou à l'application.

## Lot témoin et unités natives

| Lieu | En-tête | Matrice | Blocs de terrain |
|---|---:|---:|---|
| Bourg Geon | 60 | 0, commune aux extérieurs | 0, colonne 21, ligne 12 |
| Laboratoire du Professeur Orme, RDC | 61 | 100 | 244 |
| Route 29 | 33 | 0 | 1, 2, 3, colonnes 18 à 20, ligne 12 |
| Laboratoire, étage | 62 | 101 | 257 |
| Route 47 | 151 | 0 | 76 à 81, colonnes 2 à 4, lignes 11 et 12 |

Les libellés français sont éditoriaux ; les fichiers gardent les identifiants natifs.
`MapMatrix_MapMatrixData_Load` dans `src/map_matrix.c` définit l'ordre des sections : dimensions,
drapeaux, nom, en-têtes optionnels, altitudes optionnelles et blocs. Une matrice sans en-têtes
appartient au lieu qui la charge. La limite moteur est de 799 cellules et 16 octets de nom.
Un bloc mesure 32 × 32 cases, une case 16 unités ; `fx32` représente une unité par 4 096.
L'altitude d'une matrice se convertit par pas de huit unités, comme le chargement de terrain.

HGSS ne passe jamais par le choix binaire Platine/DP de `Gen4PretRepo`.
`pret_hgss_binary.py` lit les NARC avec contrôle des sections et des intervalles, puis les blocs :
quatre tailles `u32`, signature `u16 0x1234`, taille auxiliaire `u16`, attributs des cases,
section auxiliaire, objets, NSBMD et BDHC. `include/terrain_attributes.h` fixe l'offset des attributs
à `0x14`. `ov01_021F4AAC` dans `asm/overlay_01_021F4704.s` lit les quatre octets supplémentaires
et leur section avant les objets. Le bloc 0 exerce effectivement cette section de 88 octets.
Le bit 15 d'un attribut porte la collision, l'octet bas le comportement.

Les BDHC du lot passent le lecteur de plaques et de plans déjà utilisé par Platine ; leurs références
et leurs tailles sont contrôlées avant de calculer les hauteurs. La fixture HGSS comporte deux surfaces
superposées et une section auxiliaire, pour détecter un décalage silencieux vers le format Sinnoh.

## Rendu, acteurs et passages

`AreaDataManager_Alloc/Load` dans `asm/overlay_01_021FB878.s` sélectionne les archives natives :
zones `a/0/4/2`, listes d'objets `a/0/4/3`, textures de terrain `a/0/4/4`, textures d'objets `a/0/7/0`,
modèles extérieurs `a/0/4/0` et intérieurs `a/1/4/8`. Terrain et objets emploient leurs textures HGSS.
Les codecs Nitro, GX et le rasteriseur sont communs ; aucune archive de Sinnoh n'est substituée.
Les caches en mémoire sont bornés et vivent avec le moteur du prototype.

La projection oblique reprend l'angle de la table HGSS `ov01_02206478`, pas une valeur choisie selon
la génération. Les éclairages de jour suivent `AreaDataManager_GetAreaLightArchiveID` puis la table
`ov01_02206450`. Le prototype garde les modèles dans leur état statique initial ; il n'anime pas les
décors. Les traits blancs hors du sol de Bourg Geon proviennent du modèle natif `wind`, objet 28 ;
ils ne signalent pas un déplacement des cases ou un modèle de remplacement.

Les JSON d'événements gardent les positions, directions, scripts symboliques et drapeaux de retrait.
Les sections absentes représentent des listes vides selon `zone_event.json.txt` ; une section inconnue
est refusée. `overlay_01_sprite_data.s` relie les sprites aux fichiers NSBTX HGSS via `constants/mmodel.h`.
Chaque vue `review.png` pose un acteur témoin de face sur sa surface BDHC et annote les passages
par `index > destination:ancre`. Le drapeau de l'acteur reste présent dans la preuve : cette vue technique
n'affirme pas que tous les personnages sont simultanément visibles dans un état de scénario donné.

Les deux passages Bourg Geon ↔ laboratoire sont vérifiés dans les deux sens : RDC par l'ancre 0,
étage par l'ancre 4 de Bourg Geon. Chaque destination et chaque ancre référencées par le lot existent.
La Route 29 est reliée par continuité de matrice, sans porte inventée : sept paires de cases adjacentes
à la frontière partagent une hauteur et n'ont pas de collision.

La Route 47 exerce les niveaux superposés : 118 cases ont plusieurs surfaces BDHC. La première,
en `(97, 377)`, porte le comportement `0x15` et les hauteurs 168 et 208 unités. La vue inférieure
coupe le décor à 188 unités pour exposer le passage sous le pont. C'est une coupe technique du lieu
témoin ; le découpage éditorial de tous les plans et accès de Johto/Kanto appartient à la phase 3.

## Preuve et suite

Les [résultats synthétiques](cartes-hgss-preuve.json) conservent les empreintes relues.
Deux générations séparées ont produit exactement le même inventaire : 361 fichiers, 8 799 306 octets,
en 72,82 et 97,14 secondes sur cette machine, pendant d'autres contrôles. Aucun cache de rendu persistant
n'a été utilisé. Ces durées ne constituent pas une comparaison de performance à charge identique.
Les cinq lieux des deux versions ont les mêmes données natives et les mêmes pixels au commit retenu.
Cette égalité locale n'autorise pas à fusionner toutes les variantes HGSS.

La preuve permet de poursuivre les cartes HGSS. Les jeux restent dans `PREPARATORY_GAMES` :
ni le pipeline générique, ni la base, ni Android ne sont activés. Les prochaines cartes doivent recevoir
leur propre sélection de lieux, leurs noms français, assemblages, états initiaux et plans relus.
La résolution métier des scripts, des acteurs conditionnels et des accompagnateurs reste dans les phases
prévues du plan. Les limites de licence de la [qualification](sources-hgss.md) restent applicables avant distribution.

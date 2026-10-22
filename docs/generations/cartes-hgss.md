# Cartes préparatoires HeartGold et SoulSilver

Le prototype de phase 1 lit et rend cinq lieux depuis `pret/pokeheartgold` au commit
`6988158691eb6178cff697cda0428045ddcba5fb`, sans ROM et sans compiler le jeu.
Il reste séparé des cartes distribuées et ne rend pas HGSS disponible dans Android.

## Reproduire

Préparer les [sources qualifiées](sources-hgss.md#source-retenue-et-preuve-reproductible), puis lancer depuis la racine :

```powershell
python tools/build_data.py --hgss-maps-only
python tools/review_hgss_maps.py
python tools/check_assets.py --hgss-maps tools/build/preview/hgss-maps
cd tools
python -m pytest -q -m pipeline tests/test_hgss_map_sources.py tests/test_hgss_johto_sources.py
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

## Catalogue Johto — phase 3A

Le même point d'entrée produit désormais `johto/catalog.json`, `johto/maps/` et `johto/plans/`.
Le lot témoin des deux versions reste séparé et conserve ses collisions et sa coupe de la Route 47.
Le catalogue Johto décrit les ressources géométriques communes aux deux cartouches au commit retenu ;
les événements et les en-têtes sont comparés avant de partager les images. Cela ne fusionne ni leurs
rencontres, ni les conditions des scènes, ni les lieux spéciaux qui seront traités ensuite.

[`hgss_maps.csv`](../../tools/data/hgss_maps.csv) classe explicitement les 540 en-têtes natifs :
246 lieux de Johto, 198 de Kanto pour la phase 3B, 58 lieux spéciaux pour la phase 3C et 38 exclusions
justifiées. Le lot couvre villes, Routes 29 à 48, maisons, boutiques, Centres Pokémon, arènes,
étages des tours, Ruines d'Alpha, Caves Jumelles, Tourb'Îles, grottes et Mont Argenté.
Routes 26 à 28, Chutes Tohjo, Route Victoire et Ligue suivent le classement Kanto des sources.
Les frontières de la matrice vers les Routes 27 et 28 sont conservées, sans inventer de porte.
Les variantes du Concours de capture, des Ruines d'Alpha et du quai vide restent distinctes.

Le Casino de Doublonville, en-tête 536, est retenu malgré son indicateur régional Kanto :
sa section, son nom natif et ses portes le rattachent à Doublonville. Le Casino japonais 183
est écarté de ce lot fondé sur les sources américaines. L'ancien poste nord du Parc Naturel,
en-tête 150, garde ses six références historiques comme frontières exclues : son en-tête est marqué
`UNUSED`, il n'a aucun acteur et son unique script `D22R0201` se termine par `End`.

Les 110 plans ont un nom français et contiennent chaque lieu exactement une fois :

- Les extérieurs de la matrice 0 gardent leurs positions et altitudes DS. Les 80 voisinages de blocs
  entre lieux différents sont conservés ; ce sont des contacts géométriques, pas une preuve de
  praticabilité de toute la frontière. La continuité praticable Bourg Geon–Route 29 reste prouvée.
- Les intérieurs et salles d'un même étage sont réunis en atlas à cases espacées, sans fausse
  continuité entre deux pièces. Les origines natives, les translations, les dimensions et les
  membres de chaque plan restent dans le catalogue ; les points des deux extrémités des portes
  reçoivent ces mêmes translations.

Les 684 passages comprennent 665 liens internes, 16 frontières vers des exclusions ou des lieux
spéciaux et trois sorties d'ascenseur à destination mémorisée. Les destinations fixes et leurs
ancres sont vérifiées jusque dans les lieux hors périmètre ; une frontière n'est pas un lien navigable
vers une image absente. `FieldSystem_MapConnection` dans `src/field/field_control.c` donne le contrat
`header=0xFFF, anchor=0x100` des sorties variables. Aucune destination fixe n'est fabriquée pour elles.

La position des repères utilise le BDHC, et conserve toutes les hauteurs candidates. La surface
la plus basse sert à l'aperçu principal ; le choix des niveaux superposés relève de la phase 3C.
Une seule case d'escalier, Caves Jumelles RDC, passage 3, n'a pas de plaque BDHC : sa hauteur zéro
est explicitement documentée dans [`hgss_warp_heights.csv`](../../tools/data/hgss_warp_heights.csv).
Le champ natif `y` des portes est conservé mais ne remplace pas la hauteur du terrain.

Les [795 empreintes d'entrée Johto](cartes-hgss-johto-sources.json) complètent celles de la preuve.
Les cinq compléments de textures restent dans [`hgss_map_textures.csv`](../../tools/data/hgss_map_textures.csv),
avec les blocs concernés et leur justification ; ils proviennent exclusivement des banques HGSS natives.
Le rendu accepte les billboards face à la caméra, les enveloppes de modèles articulés et les commandes GX
d'échelle. Une restauration de matrice ne réapplique pas une seconde fois l'échelle SBC : l'Arène de
Rosalia couvre cette régression. L'éclairage fixe des grottes, dont la période unique se termine à zéro,
est distingué des périodes horaires.

Les grandes images sont rendues par cadres de 1 024 pixels au plus, puis assemblées en pyramides WebP
sans charger une image régionale entière. Leur cadre complet inclut les sommets projetés, y compris
le relief et les débords de décor. Les images par lieu sont limitées à 32 millions de pixels et les
plans à 32 768 pixels de côté. `--map-workers` choisit de un à huit processus ; chaque tâche parallèle
a un délai de 300 secondes. Les caches de modèles et de textures sont bornés ; le cache persistant
des images est indexé par les sources, codecs, corrections de textures et version de Pillow.
Son empreinte est vérifiée à la lecture. Une erreur préserve le dernier aperçu valide.

`inventory.json` couvre la preuve et Johto. Le contrôle `--hgss-maps` refuse les fichiers manquants,
modifiés ou supplémentaires, les recettes ou corrections éditoriales périmées, les plans incomplets,
les niveaux de tuiles absents et les repères hors de leur image ou de leur plan.
`review_hgss_maps.py` produit des planches de tous les lieux et plans, avec les numéros des portes,
ainsi qu'un index associant chaque vue au catalogue et aux empreintes des planches, dans
`tools/build/scratchpad/hgss-map-review/`.

La [preuve de relecture Johto](cartes-hgss-johto-preuve.json), datée du 22 octobre 2026, conserve
les empreintes des 246 images et des 24 planches : 357 vues, dont le détail des extérieurs assemblés.
La sortie validée compte 8 741 fichiers et 64 441 388 octets, preuve initiale comprise.
La dernière génération avec cache a pris 179,95 secondes ; une retouche des seuls libellés a conservé
exactement les pixels de chaque carte. Les poses des modèles sont statiques : les plateformes et
autres mécanismes d'arènes, les états de décor et les liaisons scriptées restent à finaliser en 3C.

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

La preuve et Johto permettent de poursuivre les cartes HGSS. Les jeux restent dans `PREPARATORY_GAMES` :
ni le pipeline générique, ni la base, ni Android ne sont activés. Kanto (3B), les installations,
les niveaux superposés, décors dynamiques et liaisons scriptées (3C) gardent leurs jalons propres.
La résolution métier des scripts, des acteurs conditionnels et des accompagnateurs reste dans les phases
prévues du plan. Les limites de licence de la [qualification](sources-hgss.md) restent applicables avant distribution.

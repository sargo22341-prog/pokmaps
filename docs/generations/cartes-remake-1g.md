# Cartes Remake 1G — phase 3

Rouge Feu et Vert Feuille disposent de cartes préparatoires autonomes dans
`app/src/main/assets/maps/firered-leafgreen`. Les deux versions partagent les mêmes layouts du dépôt
`pokefirered`, au commit épinglé `037335f4c725`. Elles restent non sélectionnables dans l'application :
rencontres, personnages, base Room et activation sont traités dans les phases suivantes.

## Génération et validation

`python tools/build_data.py --remake-maps-only` régénère cette branche et `assets.sha256`.
La génération complète inclut aussi les cartes Hoenn. Chaque export contient `catalog.tsv`,
`warps.tsv`, `events.json`, les tuiles WebP de 256 px et les sprites des objets visibles.
Les événements gardent leurs drapeaux, scripts, quantités, positions et paramètres d'origine.
`python tools/check_assets.py` valide aussi ce catalogue, sans cache ni réseau.

Le rendu respecte les variantes des remakes : 640 tuiles et métatuiles primaires, palettes 0–6 puis
7–12, attributs u32, bordures de dimensions variables et premières images des animations.
La taille DMA déclarée par `overworld_frame` est un produit, pas une dimension géométrique : les
bateaux utilisent des facteurs différents de leurs dimensions d'image. L'export conserve donc
les dimensions graphiques, tout en vérifiant la taille DMA. Les journaux invisibles du Memorydex
restent dans les événements, sans sprite artificiel de personnage.

## Assemblages

- Kanto assemble 37 cartes connectées depuis Bourg Palette. Safrania réelle, atteinte par ses portes,
  reste séparée : sa grande carte ne tient pas dans la petite bordure utilisée par les connexions.
  Les 38 cartes annoncées dans la reconnaissance incluaient ces deux représentations.
  Une connexion retour de la Route 6 est décalée de 12 cases ; elle est explicitement écartée dans
  `map_connection_skips.csv`, et les autres routes placent la bordure sans chevauchement.
- Les Îles Sevii réunissent 24 cartes extérieures, en sept ensembles distincts. Les six ancrages
  autour de l'Île 1 gardent un espace entre les îles, sans inventer de passage terrestre.
  Les quatre prototypes Sevii et quatre maisons inutilisées sont exclus.
- Les plans couvrent Sylphe SARL, Tour Pokémon, Grotte Azurée, Route Victoire, Îles Écume,
  Mont Braise, Ruines Tanoby et Roc Nombri. Les chemins du Rubis et du sommet du Mont Braise
  gardent des séries d'étages distinctes. Les escaliers de retour rejoignent leur sous-sol.
- Le Roc Nombri conserve l'entrée, le couloir et la bifurcation, puis deux séries indépendantes :
  montée au sommet et descente vers les profondeurs. Le Roc et l'Île Aurore portent la mention
  « Événement externe », jusque dans leurs embarcadères et salles intérieures.
- Les sept chambres Tanoby partagent un plan avec des espaces transparents. Leur ordre suit les
  entrées extérieures d'ouest en est ; leurs noms sont relus dans
  [Chambres Tanoby](https://www.pokepedia.fr/Chambres_Tanoby).
  Les noms de [Forbuissons](https://www.pokepedia.fr/Forbuissons) et
  [Agualcanal](https://www.pokepedia.fr/Agualcanal) sont distingués du Chemin Vert.
- Les plans complémentaires réunissent les cabines de chaque pont de L'Océane et les zones du
  Parc Safari. Les maisons de repos restent séparées. Grotte de Glace, Trou Percé et Tour des
  Dresseurs conservent également leurs niveaux. Aucun corridor artificiel ne relie des salles disjointes.
  Le Laboratoire de Cramois'Île, les salles de la Ligue Pokémon, la Grotte Perdue, la maison de l'Île 7,
  l'Île Aurore et le rez-de-chaussée du Roc Nombri ont aussi leur plan.
- `map_trims.csv` retire la bande d'une seule métatuile qui élargit le rez-de-chaussée de la Route Victoire
  et le 2e étage du Manoir Pokémon ; la génération refuse une bande non uniforme ou contenant un événement.
  `map_layouts.csv` affiche le tunnel de l'Île 3 creusé, le layout que son script sélectionne et qui porte
  ses événements.
- Les Îles Sevii reposent sur l'eau de bordure la plus fréquente de leurs cartes, répétée sous la carte
  (`sevii-water/<niveau>.webp`, une tuile par niveau de zoom réduite comme la carte).
- Les salles de communication à destination dynamique gardent une origine éditoriale explicite.
  Tous les autres intérieurs héritent de leur entrée ; aucune carte utilisée n'est orpheline.

Les noms français, plans, ancrages, origines et connexions écartées restent dans les CSV de
`tools/data/`, dans la famille `firered-leafgreen`, distincte de celle de Rouge/Bleu/Jaune.
Une absence de nom français arrête la génération avant toute écriture d'asset.

## Relecture et mesures du 9 octobre 2026

Les deux mondes et les 324 cartes/plans affichables ont été relus sur des planches avec
1 294 positions de warps. Les 417 zones utilisées sont toutes placées, sans chevauchement.
Le catalogue compte 504 lignes : zones, 85 plans et deux mondes.

| Mesure | Rouge Feu / Vert Feuille |
|---|---:|
| Tuiles WebP écrites | 2 226 |
| Sprites transparents | 118 |
| Fichiers finaux ajoutés | 2 347 |
| Taille, métadonnées et sprites compris | 7 327 137 octets (6,99 Mio) |
| Génération avec sources en cache | 26,8 s |
| APK debug | 87 389 861 octets (83,34 Mio) |

Aucun nouvel asset ne dépasse 5 Mio. Le plus grand, `events.json`, mesure 1 171 885 octets.
Les cartes de toutes les générations, catalogues et sprites compris, occupent 31 544 227 octets.
Les objets Git occupent 31 914 Kio avant commit, sans les fichiers nouveaux non ajoutés.
Aucune dépendance n'est ajoutée et aucun commit n'est créé par cette tâche.

Les tests vérifient noms, régions, plans, étages, événements, warps, palettes, animations,
bateaux et intégrité des fichiers. Le contrôle de reproductibilité reconstruit tous les assets
depuis les sources épinglées et compare l'inventaire SHA-256 aux fichiers du dépôt.
Le test JVM `GeneratedMapSectionsTest` vérifie aussi les séries d'étages des deux branches GBA.

L'APK est installé sur le Pixel 6 Pro ; le contrôle du téléphone porte sur le démarrage de
l'application existante avec les assets embarqués. La navigation des remakes attend la phase 6.

## Contrôles et incidents

Ruff et son formatage, validation des assets, 243 tests Python ordinaires, 131 tests du pipeline
et 293 tests JVM passent. La dernière suite pipeline termine en 245,9 s, reproductibilité comprise.
Les contrôles Android exécutés sont `ktlintCheck`, `checkNoGoogleServices`, `lintDebug`,
`testDebugUnitTest` et `assembleDebug`. Les limites de fichiers et fonctions ainsi que le diff
sont relus. Aucun asset existant ne change : l'inventaire ajoute uniquement les 2 347 fichiers
de cette branche. La base Room conserve son schéma et son contenu.

Les premiers essais ont rencontré les incompatibilités de sprites décrites plus haut, corrigées
avec tests de non-régression. Deux attentes des nouveaux tests étaient erronées : 20 journaux
au lieu des 19 présents dans pret, et un nom de propriété incorrect pour le nombre de palettes.
Les tests ont été corrigés d'après les sources et le modèle, sans affaiblir leurs vérifications.
La relecture a aussi corrigé des accents abîmés par le passage de texte dans PowerShell.

Le sandbox Windows empêchait Gradle d'utiliser son verrou de cache et pytest de relire ses
dossiers temporaires ; les contrôles ont été relancés avec les accès nécessaires. Ruff est
exécuté via `python -m ruff`, son exécutable n'étant pas dans le PATH.
La dépréciation `Configuration.setVisible(boolean)` d'AGP reste visible, comme déjà documenté
dans le README. Aucun avertissement Kotlin, Lint, Ruff ou pytest n'est masqué.
Le téléphone signale l'absence d'un fichier de trace et du paquet système `android.xr` ;
l'application reste active après un démarrage à froid, sans exception fatale.

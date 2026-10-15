# Cartes de Rouge Feu et Vert Feuille

Les cartes distribuées dans `maps/firered-leafgreen` partagent les layouts du dépôt `pokefirered`.
Les sources sont épinglées dans `tools/pokemaps_data/sources.py`.

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

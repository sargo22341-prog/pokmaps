# Cartes de Hoenn

Les cartes distribuées de Rubis/Saphir et d’Émeraude utilisent des catalogues distincts.
Les catalogues autonomes servent aussi à valider les cartes et les séries d’étages Android.

## Génération et fichiers

`python tools/build_data.py` génère aussi Hoenn. `--hoenn-maps-only` régénère seulement cette branche.
Cette option recrée aussi les catalogues des personnages et Pokémon fixes supprimés par le rendu.
Une modification des données ou de leur curation exige la génération complète, qui reconstruit la base.
Les sources pret restent épinglées et mises en cache ; aucun build Android ne lance la génération.
Chaque groupe possède `catalog.tsv`, `warps.tsv`, `events.json`, des tuiles WebP de 256 px par niveau de
zoom et ses sprites transparents dans `app/src/main/assets/maps/`. `assets.sha256` inventorie tout.
`python tools/check_assets.py` vérifie l'inventaire, la base actuelle et les deux catalogues Hoenn.

Le rendu utilise les métatuiles natives de 16 px, les trois types de couches du moteur, les retournements,
les palettes et la première image des animations aux adresses VRAM du moteur. Les sprites conservent
leurs dimensions et la première pose déclarée, même lorsque le personnage n'a qu'une vue latérale.

## Assemblages et variantes

- Les 49 cartes connectées depuis Bourg-en-Vol forment le monde extérieur. Le Parc Safari est ancré au
  nord de la Route 121 : quatre zones dans Rubis/Saphir, six dans Émeraude. La Tour de Combat ou les deux
  extérieurs de la Zone de Combat sont ancrés au sud de Nénucrique, sans inventer de liaison terrestre.
- Trois connexions incohérentes sont écartées dans `map_connection_skips.csv` ; les chemins alternatifs
  donnent une disposition sans chevauchement. Les bordures répètent leur motif original.
- Le niveau « Sous l'eau » garde les coordonnées de la surface, via `dive` / `emerge` : quatre zones dans
  Rubis/Saphir, sept dans Émeraude. Atalanopolis reste une carte séparée, rattachée à son entrée sous-marine.
- L'Île Mirage utilise le layout alternatif réellement sélectionné par le script de la Route 130.
  Elle a la taille de la carte du monde et seules les cases qui diffèrent de la route sont dessinées : elle
  apparaît en place sur le Chenal 130 (passage `mirage`), et son retour est posé dans l'eau, sous la plage.
  Les îles d'événement conservent la mention « Événement externe » dans leurs événements.
- Les cartes qu'une seule version permet d'atteindre portent cette version (`map.version_id`) : le script de
  chargement de Nénucrique ferme l'entrée de l'autre planque, ce qui rattache la Planque Magma à Rubis et la
  Planque Aqua à Saphir. Les cases que seule une version retouche au chargement forment un calque de tuiles
  propre à cette version (`hoenn-ruby`), dessiné par-dessus la carte commune : l'entrée de la Planque Magma.
- Passages sans warp (`map_warp.kind`) : plongées et remontées fixées par `setdivewarp` (Épave, Atalanopolis,
  Caverne Fondmer, Grotte Marine, Sanctuaire des Regi depuis le fond du Chenal 134), les deux stations du
  téléphérique d'après `CableCarWarp`, et les 75 entrées de Bases Secrètes vers la carte modèle de leur type.
- La Grotte Tréfonds possède deux plans distincts de marée. Les événements partagés sont résolus et les
  escaliers noyés à marée haute n'apparaissent pas comme passages praticables.
- Les plans réunissent les salles d'un même niveau ; un intervalle sépare les salles disjointes, sans
  dessiner de faux couloir. Les dimensions sont compatibles avec les deux variantes. Grotte Origine :
  cinq niveaux dans Rubis/Saphir, deux utilisés dans Émeraude. Les étages supplémentaires inutilisés sont exclus.
- Les Bases Secrètes et salles aléatoires de la Pyramide et du Reptile sont conservées comme modèles,
  avec une note explicite sur leur entrée ou assemblage variable. Leur état de partie n'est pas simulé.
- Les warps spéciaux de retour et de Base Secrète gardent une destination variable. Ceux que le moteur
  place hors du layout pour les scènes du bateau ou du Dôme restent dans les événements bruts ; aucun
  repère cliquable n'est dessiné hors carte. Les apparences dépendant du scénario sont signalées et leurs
  variables sont conservées dans les catalogues des personnages.

Les noms français de la famille sont dans `maps.csv` ; toute absence arrête la génération.
Les plans, origines et ancrages restent dans leurs CSV éditoriaux. Les cartes propres à chaque dépôt
et leurs blocs différents sont rendus séparément, sans recopier les images d'une variante sur l'autre.

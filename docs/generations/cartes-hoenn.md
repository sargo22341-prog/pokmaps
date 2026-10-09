# Cartes Hoenn — phase 3

La branche Hoenn de la phase 3 produit les assets finaux des cartes de Rubis/Saphir et d'Émeraude.
Les jeux restent déclarés mais non activés : rencontres, personnages, base Room et interface sont traités
dans les phases suivantes. Les catalogues autonomes permettent de valider les cartes dès maintenant,
y compris les sections d'étages du domaine Android, sans annoncer des jeux jouables incomplets.

## Génération et fichiers

`python tools/build_data.py` génère aussi Hoenn. `--hoenn-maps-only` régénère seulement cette branche.
Les sources pret restent épinglées et mises en cache ; aucun build Android ne lance la génération.
Chaque groupe possède `catalog.tsv`, `warps.tsv`, `events.json`, des tuiles WebP de 256 px par niveau de
zoom et ses sprites transparents dans `app/src/main/assets/maps/`. `assets.sha256` inventorie tout.
`python tools/check_assets.py` vérifie l'inventaire, la base actuelle et les deux catalogues Hoenn.

Le rendu utilise les métatuiles natives de 16 px, les trois types de couches du moteur, les retournements,
les palettes et la première image des animations aux adresses VRAM du moteur. Les sprites conservent
leurs dimensions et la première pose déclarée, même lorsque le personnage n'a qu'une vue latérale.
Les assets des six jeux actuels restent identiques octet par octet après génération complète.

## Assemblages et variantes

- Les 49 cartes connectées depuis Bourg-en-Vol forment le monde extérieur. Le Parc Safari est ancré au
  nord de la Route 121 : quatre zones dans Rubis/Saphir, six dans Émeraude. La Tour de Combat ou les deux
  extérieurs de la Zone de Combat sont ancrés au sud de Nénucrique, sans inventer de liaison terrestre.
- Trois connexions incohérentes sont écartées dans `map_connection_skips.csv` ; les chemins alternatifs
  donnent une disposition sans chevauchement. Les bordures répètent leur motif original.
- Le niveau « Sous l'eau » garde les coordonnées de la surface, via `dive` / `emerge` : quatre zones dans
  Rubis/Saphir, sept dans Émeraude. Atalanopolis reste une carte séparée, rattachée à son entrée sous-marine.
- L'Île Mirage utilise le layout alternatif réellement sélectionné par le script de la Route 130.
  Les îles d'événement conservent la mention « Événement externe » dans leurs événements.
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
  variables sont conservées pour la phase personnages.

Les noms français de la famille sont dans `maps.csv` ; toute absence arrête la génération.
Les plans, origines et ancrages restent dans leurs CSV éditoriaux. Les cartes propres à chaque dépôt
et leurs blocs différents sont rendus séparément, sans recopier les images d'une variante sur l'autre.

## Relecture et mesures du 9 octobre 2026

Les quatre assemblages mondiaux et 856 cartes/plans ont été relus sur des planches avec les repères de
passage : 485 pour Émeraude et 371 pour Rubis/Saphir, soit 1 305 et 1 152 positions de warps.
Les zones internes incluses dans un plan sont relues dans ce plan, et non comptées une seconde fois.

| Mesure | Émeraude | Rubis/Saphir |
|---|---:|---:|
| Lignes du catalogue, zones et plans compris | 543 | 416 |
| Tuiles WebP réellement écrites | 2 785 | 2 267 |
| Assets, métadonnées et sprites compris | 9,49 Mio | 7,75 Mio |

Au total : 5 324 nouveaux fichiers, dont 266 sprites, pour **18 076 488 octets**. Aucun nouvel asset
ne dépasse 5 Mio ; le plus volumineux est `emerald/events.json` (**1 690 724 octets**).
Génération Hoenn avec sources en cache : **70,1 s**. APK debug : **80 581 321 octets** (76,85 Mio),
contre 65 052 300 octets avant cette phase. Objets Git avant commit : **23 478 Kio**, sans inclure les
nouveaux fichiers non encore ajoutés à Git. Aucun commit n'a été créé par cette tâche.

Ruff, formatage, vérification des assets, 239 tests Python ordinaires et 126 tests du pipeline passent.
Le test de reproductibilité reconstruit tous les assets et compare exactement l'inventaire SHA-256.
Les tests vérifient notamment les pixels, palettes, animations, chevauchements, destinations de warps,
marées, noms, fichiers et sections d'étages. Aucune nouvelle dépendance n'est ajoutée.

Les contrôles Android (`ktlintCheck`, `checkNoGoogleServices`, `lintDebug`, `testDebugUnitTest`,
`assembleDebug`) passent, avec 292 tests JVM. Le seul avertissement de build est la dépréciation
`Configuration.setVisible(boolean)` d'AGP déjà documentée dans le README ; aucun diagnostic Kotlin
ou Lint n'est masqué.

L'APK a été installé sur le Pixel 6 Pro par ADB ; le démarrage de l'application réussit.
Ce contrôle porte sur l'application existante avec les nouveaux assets embarqués ; la navigation Hoenn
sur téléphone appartient à la phase 6.

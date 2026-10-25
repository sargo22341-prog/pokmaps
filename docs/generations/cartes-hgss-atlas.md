# Catalogue cartographique intégral HGSS — phases 3B et 3C

Ce lot étend la [preuve et le catalogue Johto](cartes-hgss.md), depuis le même commit
`6988158691eb6178cff697cda0428045ddcba5fb` de `pret/pokeheartgold`.
La génération complète utilise cet atlas pour les assets Android HGSS, sans ROM.
L'aperçu conserve 496 lieux et 224 plans techniques. L'export Android sépare les bâtiments indépendants
et réunit Johto et Kanto dans leur repère natif commun. Les 171 coupes techniques ne sont plus distribuées :
leurs portes, personnages et objets restent sur la vue supérieure de leur véritable étage.
Les 496 lieux, 42 plans et l'atlas Safari donnent 539 entrées distribuées, contre 711 auparavant.
L'atlas Safari complète ces plans sans remplacer les lieux natifs. Les gabarits Safari et les salles
de connexion sans accès géographique fixe
gardent leur ancre native dans une vue individuelle, sans leur inventer une ville d'origine.
Les salles ne partagent une vue que si une porte native les relie sur le même plan et dans le même type
de carte ; un accès extérieur ne réunit donc pas les bâtiments qu'il dessert. Les maisons isolées sont
affichables directement, avec leurs coordonnées locales et leurs portes traduites depuis l'atlas.
Les 196 coupes natives restent tracées dans le catalogue source de l'aperçu. Aucun sélecteur de coupes
n'apparaît dans le guide, y compris dans la Caverne Azurée, la Cave Taupiqueur, les Îles Écume et la Route Victoire.
Les étages et sous-sols natifs sont conservés.

## Reproduire

Depuis la racine, avec les sources qualifiées déjà préparées :

```powershell
python tools/build_data.py --hgss-maps-only --map-workers 8
python tools/review_hgss_maps.py
python tools/check_assets.py --hgss-maps tools/build/preview/hgss-maps
cd tools
python -m pytest -q -m pipeline `
  tests/test_hgss_map_sources.py tests/test_hgss_johto_sources.py tests/test_hgss_atlas_sources.py
```

`tools/build/preview/hgss-maps/atlas/catalog.json` réunit les deux régions et les lieux spéciaux.
`johto/catalog.json` conserve le périmètre de 3A. Les fichiers restent dans l'aperçu ignoré par Git ;
les inventaires éditoriaux, les empreintes des sources et la preuve de relecture sont versionnés.
Une génération qui échoue conserve le dernier aperçu publié localement.

## Kanto et installations

L'inventaire classe les 540 en-têtes : 246 lieux de Johto, 192 de Kanto, 58 lieux spéciaux ou gabarits et
44 exclusions justifiées. Chaque lieu retenu possède un nom français, un plan et un étage.
Les deux versions partagent les géométries natives contrôlées, sans fusionner leurs rencontres ou leur scénario.

Kanto couvre ses villes, Routes 1 à 28 présentes dans HGSS, Forêt de Jade, Cave Taupiqueur,
Mont Sélénite, Grotte Sombre, Caverne Azurée et Îles Écume, avec leurs étages et l'Arène de Cramois'Île.
Les Routes 26 à 28, Chutes Tohjo, Route Victoire et la Ligue conservent le classement régional natif.
La Centrale en panne et réparée, la danse des Mélofée et le quai vide restent des variantes distinctes.
Les six en-têtes retirés du lot Kanto sont les cinq `UNUSED` 148, 406, 416, 458 et 468 et le Casino japonais 381.
Le Casino américain 537 expose la Voltorbataille ; les récompenses restent dans la salle 382.
Deux constantes historiques sont corrigées par les ressources natives : le `POKECENTER_2F` de Safrania
utilise la matrice des sous-sols et l'escalier descendant du RDC ; le poste `ROUTE_19_ROUTE_12`
appartient à la Route 11 et ses portes relient exclusivement les Routes 11 et 12.

Les installations comprennent la Zone de Combat, le Pokéathlon, le Parc Safari, l'Aquaria,
le Terminal Mondial, les salles de connexion, les Ruines Sinjoh et les trois salles de la Tour Enfouie.
Une image de salle de connexion ne promet pas la disponibilité actuelle d'un ancien service en ligne.
Les douze habitats du Safari et ses deux gabarits supplémentaires restent identifiés séparément.
`safari` décrit les six emplacements de la matrice 212, leurs gabarits de terrain et les dix configurations
initiales de `sSafariZoneDefaultAreaSets`. Aucun agencement personnalisé de six habitats ni objet posé
par le joueur n'est présenté comme une configuration universelle. Le `native.json` garde la matrice
complète, y compris ses emplacements vides que le moteur remplit selon la sauvegarde.

Les extérieurs de Johto et de Kanto suivent les positions et altitudes de la matrice DS 0.
Le monde distribué réunit les deux régions, le Mont Argenté, les Routes 26 à 28 et la Ligue dans ce même repère.
Les raccords utilisent une profondeur commune, comme dans les aperçus régionaux. Les autres plans assemblent les salles
avec des espaces, sans créer de continuité praticable entre deux pièces.

## Portes et déplacements de scénario

L'atlas conserve 1 314 portes natives, leurs ancres et leurs surfaces BDHC candidates.
Une porte vers une exclusion reste une frontière ; une sortie à destination mémorisée reste variable.
Les coordonnées des deux extrémités suivent les translations de leurs plans respectifs.

`script_navigation` conserve les commandes `Warp`, `MoveWarp`, `SetDynamicWarp`, `ScrCmd_722` et
`ScrCmd_723`, avec fichier, ligne, étiquette et arguments natifs. Ce sont des branches de scénario,
pas des portes ouvertes sans condition. Les conditions restent rattachées à leur script source qualifié ;
l'inventaire ne simule ni sauvegarde ni exécution du jeu.

Les deux commandes de train relient les quais vides 519 et 520 aux quais d'arrivée 401 et 198.
Les deux commandes d'embarquement des ports 330 et 387 conduisent à l'Aquaria 307 en `(24, 19)`.
`ScrCmd_722` et `ScrCmd_723` lisent deux octets, puis destination, x et z dans `src/scrcmd_c.c`.
Le contrôle du Passe Train se trouve dans les scripts des contrôleurs ; le bateau conserve
`VAR_BOAT_DIRECTION` et `FLAG_BOAT_ARRIVED`, ainsi que ses deux portes alternatives.
Les ascenseurs conservent les destinations candidates de `SetDynamicWarp` sans transformer une sortie
mémorisée en destination fixe inconditionnelle.

Au Mont Sélénite, le script `D02R0102` déplace quatre portes selon le jour et la scène des Mélofée.
Les portes 4 et 5 de l'en-tête 448 sont garées hors BDHC dans les événements natifs.
Leur hauteur de projection est justifiée dans `hgss_warp_heights.csv` par le palier des positions actives.
Les positions garées et les instructions de déplacement restent toutes conservées dans l'aperçu.
`hgss_guide_passages.csv` écarte seulement ces deux portes inactives du guide ; les sorties normales du square
et sa boutique (en-tête 518) sont accessibles sur la vue supérieure.

À Parmanie, l'en-tête 479 ne possède qu'une sortie native vers la ville. Le préposé lance
`Warp MAP_PAL_PARK, 0, 24, 47, DIR_NORTH` dans `scr_seq_0812_T08R0201.s`.
`hgss_script_passages.csv` ajoute cet accès au guide en vérifiant l'instruction dans la source épinglée.
Le Parc des Amis sert aux transferts GBA ; il est distinct du Parc Safari de Johto.

## Surfaces superposées et décors

Chaque `native.json` inventorie toutes les cases dont le BDHC possède plusieurs surfaces.
Les images principales et les coupes utilisent le même cadre complet, comprenant relief et débords des modèles.
Les coupes sont distinctes des étages : entre deux surfaces séparées d'au moins un pas vertical de matrice
(huit unités), une image au plafond médian expose la surface inférieure.
Chaque coupe conserve plafond, cases témoins, empreinte des pixels et pyramide WebP.
Les petites intersections de plaques restent dans l'inventaire, sans produire de faux étages.
Une candidate située sous toute la géométrie visible reste dans `nonvisual_slices`, avec ses témoins
et sa justification ; elle ne produit aucune image vide. Les Îles Écume, quatrième sous-sol, exercent ce cas.
Une coupe géométrique ne prouve pas à elle seule la praticabilité de chaque surface.

Douze décors créés par le moteur complètent le terrain : ascenseur de Mauville en bas, quatre nacelles
de Mimigal à Écorcia, trois plateformes à Ébènelle et quatre bougies allumées à Rosalia.
`hgss_dynamic_props.csv` conserve modèles, positions, rotation et justification ; les fichiers
`src/gymmick_init.c` et `src/field/gymmick/*.c` font partie de la qualification.
Les animations et autres décors gardent leur pose native initiale ; aucune interaction n'est simulée.
Les contrats de variantes du Safari sont qualifiés séparément des entrées de rendu : leur évolution
invalide le catalogue, sans modifier arbitrairement les pixels des gabarits.
Les recettes des bitmaps et du catalogue sont distinctes : modifier la navigation, les assemblages ou
la sélection des coupes invalide les métadonnées, tout en permettant la réutilisation des images dont
les entrées de rasterisation sont inchangées.

Les images natives ne suffisent pas à assembler les extérieurs par simple superposition : un sol
voisin peut alors recouvrir le haut d'un arbre, un toit ou le pont de la Route 24. Les tuiles où les
pixels visibles de plusieurs lieux se croisent sont rendues avec une profondeur commune, depuis
leurs modèles natifs. Les autres tuiles réutilisent les images séparées. Le cadre et les coordonnées
restent identiques à ceux du catalogue ; la réduction des niveaux de zoom suit ce raccordement.
Après régénération de l'aperçu, `python tools/build_data.py --hgss-world-only` réexporte le monde
Johto–Kanto et ses inventaires. Ce réexport refuse toute modification du catalogue hors recette
d'assemblage ; un changement de géométrie ou de données demande une génération complète.

Les compléments de textures proviennent exclusivement des banques HGSS : `bike_02_2` dans la banque 27
et le sol du restaurant de Céladopole dans la banque 39. Le modèle 177 de la Sylphe SARL exerce
la matrice d'effet Nitro et la commande `PRJMAP`. Le codec commun suit le biais de texture,
la matrice d'effet et la position monde après annulation de la vue, selon
[`NNSi_G3dFuncSbc_PRJMAP`](https://github.com/pret/pokediamond/blob/b623abef1b4d/arm9/asm/NNS_G3D_sbc.s).
Cela réutilise le contrat du codec DS, sans substituer de modèle ou de texture de Sinnoh.

## Contrôles

L'inventaire global SHA-256 couvre la preuve initiale, Johto et l'atlas. Le contrôleur refuse les fichiers
absents, modifiés ou supplémentaires, les sources éditoriales périmées, les images aux dimensions ou
pixels incohérents, les niveaux de tuiles absents et les membres de plans ou repères invalides.
Les planches indexent lieux, coupes et plans, avec un détail de chacune des deux régions.
La preuve versionnée conserve leurs empreintes et celles des images.

La [preuve du 24 octobre 2026](cartes-hgss-atlas-preuve.json) couvre 496 cartes et gabarits,
224 plans, 196 coupes et une candidate non visuelle : 918 vues sur 60 planches.
Les 1 314 portes comprennent 1 299 liens internes, neuf destinations mémorisées et six références
historiques au poste inutilisé 150. Les 181 instructions de déplacement comprennent les quatre
transports du train et de l'Aquaria. Les 1 771 fichiers natifs et les trois contrats du Safari sont qualifiés.
L'aperçu complet, preuve et catalogue Johto compris, compte 28 977 fichiers et 216 699 340 octets.
La dernière génération avec cache, sur quatre processus, a pris 958,18 secondes.
Les pixels des cartes natives et coupes restent identiques. Les huit raccords signalés et six autres
frontières de Johto ont été relus après correction de la profondeur commune. La planche 49 et les
deux vues détaillées régionales ont changé ; les 57 autres planches restent identiques.

## Guide commun et mesures sur téléphone — 25 octobre 2026

Les assets cartographiques HGSS passent de 10 040 fichiers et 52 128 283 octets à 7 374 fichiers
et 39 628 972 octets, soit 12 499 311 octets économisés (24 %). Les cartes des autres jeux sont inchangées.
Ces chiffres portent sur les ressources versionnées, pas sur la taille compressée de l'APK.

Sur le Pixel 6 Pro en 1 440 × 3 120, l'APK debug a été mesuré avec `dumpsys gfxinfo` et `meminfo` :
douze balayages horizontaux alternés de 800 pixels en 300 ms, après réglage du zoom par gestes.
Les échelles candidates ont été comparées avant de fixer le dézoom minimal à 1,0 (taille native).

| Vue du monde commun | Médiane | 95e percentile | Images hors délai |
|---|---|---|---|
| Dézoom complet sans limite | 61 ms | 1 500 ms | 75,56 % |
| Échelle 0,25 | 15 ms | 350 ms | 21,51 % |
| Échelle 0,5 | 9 ms | 53 ms | 13,69 % |
| Limite finale 1,0, après réinstallation | 9 ms | 34 ms | 5,02 % |

La dernière série compte 279 images et 271 937 Kio de PSS ; le 99e percentile reste à 40 ms.
Une série préalable à l'échelle 1,0 donnait 24 ms au 95e percentile et 1,02 % d'images hors délai.
Ces mesures décrivent les gestes testés sur cet appareil ; elles ne constituent pas une garantie de fréquence constante.
La limite reste appliquée après rotation et ne change pas le dézoom des grottes ni des autres jeux.

Les accès entrée du square → square → boutique et bâtiment de Parmanie → Parc des Amis ont été parcourus
sur le téléphone. Dans la Caverne Azurée, le pont reste visible et une échelle du RDC rejoint bien le 1er étage.
La recherche ne propose plus les coupes techniques de la Cave Taupiqueur, de la Caverne Azurée ou des Îles Écume.
La preuve de couverture est régénérée après retrait des deux points d'arbres masqués au sud d'Azuria.

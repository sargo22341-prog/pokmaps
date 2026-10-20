# Cartes de Sinnoh

`maps_gen4.py` construit deux familles depuis les matrices, modèles Nitro, textures et événements
de `pokediamond` et `pokeplatinum`. Aucun contenu de ROM n'est nécessaire.
Les détails du rendu et des lecteurs sont dans le [pipeline](../donnees/pipeline.md#lecteurs-ds).

La projection oblique utilise un sol de 16 pixels par case et un rasteriseur entier, sans GPU.
Les tuiles WebP sans perte mesurent 256 pixels. Les textures automatiques sont évaluées à l'image zéro.
Les surfaces BDHC praticables fournissent les niveaux inférieurs, séparés des étages du bâtiment.
Le décor mécanique reste dans son état initial, sans simulation du joueur.

`map_assemblies_gen4.csv` réunit les salles d'un même étage. Images, personnages, rencontres,
objets et deux extrémités des passages reçoivent la même translation ; les points éditoriaux restent
dans les coordonnées natives. Les personnages de face et les duos espacés dégagent les accès.

Les exclusions sont motivées dans `map_exclusions_gen4.csv`, les niveaux écartés dans
`map_level_skips_gen4.csv` et les portes vers des copies abandonnées dans `map_connection_skips.csv`.
Les événements techniques restent dans les catalogues source sans créer de repère inutile.
Le Monde Distorsion garde ses plans et connexions ; le Souterrain garde ses modèles de blocs.

Pour relire les images réellement distribuées :

```powershell
python tools/review_gen4_maps.py --maps app/src/main/assets/maps
```

Les planches, sprites et index restent dans `tools/build/scratchpad/gen4-map-review/`.
Les tests `test_gen4_cartography`, `test_gen4_assemblies`, `test_gen4_visual_regressions` et
`test_gen4_audit` couvrent géométrie, passages, apparences et données exportées.

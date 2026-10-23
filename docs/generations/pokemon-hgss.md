# Aperçu Pokémon HeartGold et SoulSilver

La phase 2 du [plan](../../plan4g%20remake.md) prépare les données Pokémon sans attendre les cartes
complètes. Depuis la phase 8, les jeux sont dans `GAMES` et leurs données rejoignent la base distribuée,
avec un export HGSS distinct des générateurs de cartes Sinnoh. Le schéma Room 23 est conservé.

## Générer et relire

Depuis la racine, avec le cache HGSS préparé selon la [qualification](sources-hgss.md) :

```powershell
python tools/build_data.py --hgss-pokemon-only
cd tools
python -m pytest -q tests/test_hgss_pokemon_sources.py tests/test_hgss_preparation.py -m pipeline
```

Sortie : `tools/build/preview/hgss-pokemon/`. `--preview` change son dossier parent et `--assets`
permet de choisir les assets versionnés dont les sprites sont réutilisés. Les sources natives et les
CSV utilisés sont contrôlés contre [l'inventaire épinglé](pokemon-hgss-sources.json) avant lecture.
Les identités 15/16 et le groupe 10 sont comparés aux CSV, sans activation implicite.
Les fichiers source absents ou modifiés provoquent une erreur nommée ; aucune ROM n'est nécessaire.

| Fichier | Contenu |
|---|---|
| `pokemon.json` | 493 espèces, régional Johto de 256 rangs, profils, attaques, CT/CS, tuteurs, évolutions et formes |
| `comparison.json` | Résultat des comparaisons natives/PokéAPI, dont les cinq écarts de capture expliqués |
| `sources.json` | Commits, empreintes des entrées natives/CSV, corrections éditoriales et sprites réutilisés |
| `sprites/` | Sprites fixes/animés, normaux/chromatiques, et planche native séparée de Pichu Troizépi |
| `inventory.json` | SHA-256 de chaque sortie, utilisable pour comparer deux générations |

L'aperçu est un catalogue JSON autonome, sans base de rencontres artificiellement vide et sans cartes.
Les identifiants natifs et paramètres bruts sont conservés avec les conditions françaises. Chaque forme
porte explicitement sa cartouche, le membre personnel natif, son profil et ses attaques par niveau/tuteur.
La génération se fait dans un dossier temporaire voisin ; le remplacement n'arrive qu'après validation.
Un échec conserve l'aperçu précédent, y compris si le remplacement final échoue.

## Sources et comparaisons

Le commit HGSS est `6988158691eb6178cff697cda0428045ddcba5fb` ; les CSV PokéAPI sont ceux de
`bc92d3b6029ef1abe9e7ad424c400b338f3c11fe`. Aucun lecteur DP/Platine ou GSC ne fournit de valeur de secours.

- `personal.json` : les 493 espèces viennent des membres 1–493 ; 0, 494 et 495 sont techniques.
  Les douze profils alternatifs des membres 496–507 restent séparés. Statistiques, types, talents,
  objets tenus, capture, bonheur initial, reproduction et compatibilité CT/CS sont conservés depuis HGSS.
- `wotbl.narc` : 508 listes de mots 16 bits ; niveau sur sept bits, attaque sur neuf, terminaison
  `0xffff` et éventuel alignement nul. Les niveaux et identifiants sont bornés et chaque membre est contrôlé.
- `waza_tbl.narc` : 471 membres, dont 467 attaques jouables. Le membre 0 et les entrées techniques
  468–470 ne sont pas des attaques apprenables. Les profils de seize octets conservent notamment puissance,
  précision, PP, classe physique/spéciale/statut et priorité signée.
- `src/item.c` : 92 CT et huit CS, comparées aux machines du groupe 10. La CS05 est Siphon,
  jamais Anti-Brume repris de Sinnoh.
- `waza_oshie.json` : compatibilités des 493 espèces et des douze profils alternatifs ; Coup d'Boule inclus.
  Le moteur `scrcmd_move_tutor.c` atteste l'indexation des formes et la table des tuteurs.
- Les attaques complémentaires par reproduction, tuteurs spéciaux et autres méthodes sont conservées
  à part sous `supplementary_moves`, depuis les seules lignes PokéAPI du groupe 10. Cette provenance est
  explicite : la comparaison native des tuteurs porte sur la table `waza_oshie`, pas sur ces compléments.
- `evo.json` : 230 entrées sources ; toutes les chaînes sont comparées aux espèces PokéAPI.
  Les méthodes et paramètres HGSS sont conservés et traduits ; une méthode inconnue bloque la génération.
- `johtozukan.narc` : 494 rangs indexés par espèce, dont 256 non nuls, continus et identiques à PokéAPI.
  Le National comprend 493 espèces ; cela ne signifie pas qu'elles sont toutes capturables localement.

Les statistiques et types sont comparés à leur historique de génération 4, les talents sans talent caché.
Les attaques par niveau, compatibilités CT/CS et tuteurs de la table principale concordent intégralement.
Les taux de capture PokéAPI n'ont pas cet historique : Kyogre/Groudon valent 5 dans HGSS contre 3,
Rayquaza 3 contre 45, Dialga/Palkia 30 contre 3. Ces cinq écarts précis sont documentés dans
`tools/data/hgss_pokemon_rules.json` ; toute différence supplémentaire bloque l'export.

## Formes, évolutions et accès

`tools/data/hgss_pokemon_forms.csv` est un catalogue propre à HGSS : 47 formes nommées par cartouche,
avec les noms français et chemins des sprites déjà distribués. Il fournit les 94 profils de formes
distribués pour les versions 15 et 16.
Les statistiques des formes viennent de HGSS : Motisma Chaleur reste Électrik/Spectre, par exemple.
Morphéo et Arceus conservent une règle de type de combat distincte de leur profil personnel ;
aucun type Fée ni talent caché moderne n'est ajouté.

Zarbi dispose des 28 sprites A–Z, ! et ?. Les groupes des puzzles sont vérifiés contre
`EncounterGen_ChooseUnownForm` : Kabuto A–J, Ptéra R–V, Amonita K–Q, Ho-Oh W–Z.
Le moteur utilise ! et ? pour la salle d'entrée de l'événement Sinjoh et la radio peut favoriser
les lettres non capturées des groupes débloqués. Les emplacements et probabilités relèvent de la phase 4.

Les métadonnées distinguent les accès par échange, autre jeu et événement : Deoxys et ses météorites,
les appareils de Motisma, Gracidée, Orbe Platiné et Plaques. Les références aux scripts et au moteur
figurent dans les corrections éditoriales et leur empreinte entre dans `sources.json`.
`MapHeader_GetMapEvolutionMethod` renvoie toujours `EVO_NONE` : Magnézone, Tarinorme, Phyllali et Givrali
exigent une évolution dans Sinnoh, puis un échange. Les échanges évolutifs restent distincts.

Pichu Troizépi est une exception explicite : événement au Bois aux Chênes, aucune évolution ni échange.
Il n'existe pas dans Noir/Blanc. Son aperçu conserve donc la planche HGSS native de 160 × 80 pixels,
hors des variantes Noir/Blanc ; aucun sprite ordinaire ou chromatique de substitution n'est inventé.
Les autres sprites réutilisent les assets Noir/Blanc contrôlés par leur SHA-256 et par l'égalité des
pixels du fixe avec la première image animée. Aucun téléchargement de sprites n'est nécessaire.

## Vérifications

Les tests ordinaires couvrent décodage, bornes, erreurs, évolutions non locales, isolement des sorties
et restauration d'un aperçu après échec de remplacement. Les tests `pipeline` contrôlent les empreintes,
les comparaisons exhaustives et les profils par cartouche, dont Motisma, Deoxys, Shaymin et Cheniselle.
Les cartes, rencontres, obtentions détaillées et services sont reliés par la génération complète.

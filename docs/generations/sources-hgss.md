# Qualification des sources HeartGold et SoulSilver

Contrat préparatoire de la phase 0 du [plan](../../plan4g%20remake.md), établi le 21 octobre 2026.
Les quatorze jeux distribués restent seuls actifs. Aucun rendu HGSS n'est encore validé.

## Source retenue et preuve reproductible

Source : [pret/pokeheartgold au commit retenu][source-hgss].

[source-hgss]: https://github.com/pret/pokeheartgold/tree/6988158691eb6178cff697cda0428045ddcba5fb
Le commit complet est figé dans `sources.HGSS_PRET_COMMIT`, séparément de `PRET_COMMITS` :
la génération actuelle télécharge tous les éléments de cette dernière table.
Le README source annonce HeartGold US et SoulSilver US ; `Makefile` choisit `HEARTGOLD` ou `SOULSILVER`.
Le code reste partiellement en assembleur. Aucun jeu n'a été compilé et aucune ROM n'a été utilisée.

L'[inventaire vérifiable](sources-hgss.json) conserve les SHA-256 des fichiers de référence, les comptes
et les identités des autres sources. Il décrit ce commit, jamais la branche mouvante `master`.
Les fins de ligne des textes sont normalisées en LF avant empreinte pour neutraliser `core.autocrlf`.
Pour remettre les sources d'audit en cache, sans les intégrer au pipeline :

```powershell
git clone --no-checkout https://github.com/pret/pokeheartgold.git tools/.cache/hgss-qualification
git -C tools/.cache/hgss-qualification checkout 6988158691eb6178cff697cda0428045ddcba5fb
cd tools
python -m pytest -q tests/test_hgss_preparation.py -m pipeline
```

Le test refuse un fichier différent de l'inventaire. Les tests ordinaires restent sans réseau ni cache HGSS.
Les sources brutes restent exclues de Git. Les futures extractions conservent version, commit,
chemin, membre/entrée natif, transformation et correction éditoriale éventuelle.

## Matrice de provenance

Les chemins suivants sont relatifs au dépôt pret. « Présent » signifie inventorié et lisible,
sans prétendre que le lecteur métier ou le rendu a déjà été réalisé.

- **Identités et régions** : `include/constants/maps.h`, `src/data/map_headers.h`, `include/map_header.h` ; 540
  identifiants natifs, dont entrées techniques ; régions portées par les en-têtes. Aucun catalogue utile de 540 lieux
  promis.
- **Matrices** : `files/fielddata/mapmatrix/map_matrix/*.bin` ; 288 matrices ; format, unités et altitudes à éprouver en
  phase 1.
- **Terrain et collision** : `files/a/0/6/5`, `src/terrain_attributes.c`, `include/filesystem_files_def.h` ; Archive
  NARC présente, 676 membres ; identifiant moteur 65. Décodage des blocs et BDHC à prouver.
- **Décors et textures** : `files/a/0/4/0`, `files/fielddata/build_model/bm_field.narc`, `bm_room.narc`, archives
  numériques sous `files/a/` ; Présence des ressources binaires ; association zones/modèles/palettes non validée par cet
  inventaire. Aucun alias avec les archives Sinnoh.
- **Événements et passages** : `files/fielddata/eventdata/zone_event/*.json`, `zone_event.json.txt` ; 491 tables JSON ;
  acteurs, portes et déclencheurs à lire avec leur contrat HGSS.
- **Scripts et objets** : `files/fielddata/script/scr_seq/`, `asm/macros/script.inc`, `include/constants/scrcmd.h` ; 965
  fichiers `.s`, 536 `.h` ; en-têtes inclus. Résolution des commandes et conditions en phase 5.
- **Textes** : `files/msgdata/msg/*.json` ; 828 banques anglaises, pas de traduction française intégrale du jeu.
- **Sauvages ordinaires** : `files/fielddata/encountdata/gs_enc_data.json`, son `.json.txt`, `src/encounter.c` ; 142
  tables ; variantes imbriquées HG/SS. Le template choisit `ENC_HEARTGOLD`/`ENC_SOULSILVER`, le moteur `ENCDATA_NARC`.
- **Arbres, concours, Safari** : `files/arc/headbutt.json`, `files/data/mushi/mushi_encount.csv`,
  `files/arc/safari_enc.json` ; 540 entrées d'arbres (dont vides), 12 zones Safari ; lire aussi moteur et conditions
  avant tout taux affiché.
- **Pokémon** : `files/poketool/personal/personal.json`, `personal.json.txt`,
  `include/struct_defs/personal_narc_structs.h` ; 508 entrées techniques et formes comprises ; ce compte n'est pas celui
  des espèces.
- **Évolutions, attaques, tuteurs** : `files/poketool/personal/evo.json`, `wotbl.narc`,
  `files/poketool/waza/waza_tbl.narc`, `files/fielddata/wazaoshie/` ; 230 entrées d'évolution ; archives et tables
  disponibles, sémantique à comparer à PokéAPI.
- **Équipes** : `files/poketool/trainer/trainers.json`, templates `trdata.json.txt`, `trpoke.json.txt` ; 738 entrées ;
  scènes, revanches et variables à résoudre séparément.
- **Régional Johto** : `files/poketool/johtozukan.narc`, `src/pokemon.c`, `include/constants/johto_dex.h` ; Membre 0 :
  494 entiers 16 bits indexés par espèce, dont 256 rangs non nuls ; égalité exacte avec PokéAPI épinglé.
- **Capture et reproduction** : `src/encounter.c`, `src/daycare.c`, code de combat sous `src/battle/` ; Sources
  présentes ; aucune équivalence des règles avec GSC ou Sinnoh déclarée.
- **Activités** : `src/pokewalker.c`, `src/safari_zone.c`, `src/overlay_03/custom_safari_zone.c`,
  `include/constants/pokewalker_courses.h` ; Points d'entrée ; couverture exhaustive des récompenses et parcours à
  établir en phase 7.
- **Sprites des fiches** : PokeAPI/sprites au commit déjà épinglé dans Pokémaps ; Convention Noir/Blanc conservée ;
  formes et accès HGSS à contrôler en phase 2.
- **Français** : CSV PokéAPI épinglés et corrections relues `tools/data/` ; Noms des versions confirmés ; pas de reprise
  automatique des noms/lieux GSC par identifiant.
- **Succès** : Archives locales `7212.json`, `39076.json`, `index.json` ; 136 succès communs, entrée SS vide ; aucune
  traduction HGSS dans `gen4_fr.csv`.

Les correspondances initiales de phase 1 sont déjà identifiées :

- **Bourg Geon** : `NEW_BARK` (60 / T20) ; 0 EVERYWHERE ; 057 T20 ; 0842 T20 ; 0542 T20
- **Laboratoire du Professeur Orme, RDC** : `NEW_BARK_ELMS_LAB_1F` (61 / T20R0101) ; 100 ; 058 T20R0101 ; 0843 T20R0101
  ; 0543 T20R0101
- **Route 29** : `ROUTE_29` (33 / R29) ; 0 EVERYWHERE ; 030 R29 ; 0225 R29 ; 0373 R29

Ces libellés sont des correspondances éditoriales, pas une traduction extraite des banques anglaises.
Le découpage des extérieurs dans la matrice commune doit encore être démontré.

## Contrat et isolement des jeux

`hgss_preparation.py` expose `HEARTGOLD_SOULSILVER` dans `PREPARATORY_GAMES` uniquement.
Ce contrat n'entre ni dans `GAMES`, ni dans `GAMES_IN_PROGRESS`, ni dans `ALL_GAMES`/`DECLARED_GAMES`.
Cette séparation est nécessaire : `_build_all` génère automatiquement `ALL_GAMES`, alors que
`Gen4PretRepo` ne reconnaît que Platine/DP et que certains lecteurs choisissent DP par défaut.
Le passage à `GAMES_IN_PROGRESS` exige d'abord un aiguillage HGSS explicite et la preuve de phase 1.

- **Versions PokéAPI** : 15 `heartgold` → Or HeartGold ; 16 `soulsilver` → Argent SoulSilver.
- **Groupe** : 10 `heartgold-soulsilver`, génération 4, remake de génération 2.
- **Famille** : `heartgold-soulsilver`, réservée ; géométrie partagée à confirmer avant assemblage.
- **Régions** : Johto puis Kanto ; origines natives `NEW_BARK` (60), `PALLET` (49).
- **Identifiants composites** : Johto 993, Kanto 992, hors 0–539 et distincts des régions actuelles 994–999.
- **Jaquettes** : Ho-Oh / Lugia ; couleurs selon la convention Or/Argent existante.
- **Pokédex** : `updated-johto` (7), 256 rangs continus et uniques ; National 493, déblocage requis.
- **Format** : `GEN4` décrit la plateforme ; il n'autorise aucun appel implicite au lecteur Sinnoh.
- **Base, Android, sauvegardes** : Aucune activation, extension SQL, modification des enums ou écriture de progression
  en phase 0.

Les CSV de référence sont ceux du commit `bc92d3b6029ef1abe9e7ad424c400b338f3c11fe` :
`versions`, `version_groups`, `version_names` (langue 5), `pokedexes`, `pokedex_version_groups`,
`pokemon_dex_numbers`. Leurs empreintes sont dans l'inventaire avec celles des sources natives.

## Capacités, contenus et dépendances de génération

Les capacités suivantes sont dans le périmètre ; leur implémentation reste conditionnée à la lecture HGSS.
Elles ne sont pas déduites du seul numéro de génération.

- **Pokémon** : Statistiques historiques, talents, capacités, CT/CS, tuteurs, évolutions, formes, Zarbi,
  régional/National ; Sources Pokémon + CSV + sprites épinglés → `hgss-pokemon`. Aucune carte complète requise.
- **Cartes** : Johto/Kanto, intérieurs, étages, ponts, collisions, décors initiaux, portes, train, bateaux, Vol ; Preuve
  Bourg Geon/intérieur/Route 29 dans les deux versions, puis lieu superposé → `hgss-maps`.
- **Rencontres** : Marche, eau, cannes, horaires, essaims, radio, Coup d'Boule, Éclate-Roc ; Moteur + tables + cartes
  validées → `hgss-encounters`. Aucun filtre Miel/Pokéradar/double insertion hérité.
- **Conditions complexes** : Concours, Safari, blocs et maturation ; fixes, errants, dons, œufs, échanges ; Modèle borné
  de configurations et étapes ; aucun taux inconditionnel fabriqué.
- **Personnages** : Équipes, starter, scénario, revanches Pokématos, objets, services, boutiques, tuteurs, Noigrumes ;
  Cartes + scripts + équipes + conditions + français relu → `hgss-characters`.
- **Règles** : Balls Noigrumes, Safari/concours, bonheur, reproduction, objets Pouvoir et Pierre Stase ; Comparaison du
  moteur HGSS avant réutilisation des formules ; tests purs par groupe de versions.
- **Activités** : Pokéathlon, Noigrumes à boire, Pokéwalker, radio, Pokématos, concours, photos, Zone de Combat ;
  Catalogues et guides propres → `hgss-content`. Comparaison à Platine avant tout partage.
- **Collection et guides** : Aventure Johto, Kanto, Red, après-jeu, objectifs cartouche seule, calendrier, errants et
  formes ; Tous les catalogues requis validés ; compatibilité des sauvegardes historiques.
- **Externe** : Distributions, Pokémon déclencheurs, transferts, parcours externes ; Provenance et conditions ;
  accessoire Pokéwalker séparé d'événement externe, exclu des objectifs cartouche seule.
- **Succès** : Ensemble officiel commun, traduction française, progression manuelle ; Archives locales + association
  testée des deux versions à 7212 ; aucune génération en phase 0.

Ces noms d'aperçu restent réservés : aucune option `--hgss-…-only` n'est encore disponible.
Chaque futur aperçu vérifiera commit et empreintes de ses prérequis avant export ; les jeux actuels ne
doivent pas être régénérés pour préparer HGSS. Aucun changement de schéma ne découle de cette qualification.

## Variantes régionales et succès

Édition de référence retenue : mécanique des versions US fournies par pret, présentation française.
Le code `VoltorbFlip_LaunchApp` dans `src/launch_application.c` et son appel dans
`src/field/scrcmd_pokemon_misc.c` prouvent la présence du Voltorbataille dans cette branche.
Les machines japonaises ne seront pas substituées au Casino de cette édition.
Cette décision ne prouve pas l'identité intégrale US/Europe : les différences utiles seront indiquées
dans les guides ; toute divergence touchant une donnée promise bloque son export jusqu'à résolution.
Les textes du jeu ne sont pas intégralement traduits ; noms propres, conditions et descriptions visibles
doivent passer par PokéAPI/corrections françaises puis les ressources Android.

HeartGold et SoulSilver utiliseront tous deux le set 7212 (136 succès archivés le 12 octobre 2026).
39076 reste une archive vide, jamais une source de succès de remplacement. Les identifiants officiels
restent inchangés. L'association Android et la synchronisation seront implémentées et testées en phase 7E ;
les traductions existantes ne couvrent pas HGSS. Aucun appel authentifié ni export actualisé n'est nécessaire ici.

## Licences, lacunes et portes de sortie

Le dépôt candidat ne fournit pas de licence globale à sa racine. Les licences des outils embarqués
(`tools/nitrogfx/LICENSE`, `tools/jsonproc/nlohmann/LICENSE.MIT`, `tools/msgenc/LICENSE.pugixml.md`)
ne constituent pas une licence des graphismes ni du jeu. La licence MIT de Pokémaps ne les couvre pas.
Conserver les crédits Nintendo/Creatures/GAME FREAK et la provenance ; décider les mentions adaptées
avant de distribuer de nouveaux assets. Aucun avis de réutilisation juridique n'est déduit de GitHub.

- **Ressource nécessitant une ROM externe** : Aucune identifiée pour les fichiers inventoriés : données natives et
  archives déjà versionnées. L'exhaustivité des futurs contenus n'est pas prouvée.
- **Preuve de rendu sans ROM** : Non réalisée ; jalon de phase 1, bloquant les cartes globales. Il faut résoudre zones,
  textures, modèles, BDHC et sprites de terrain, puis comparer HG/SS.
- **Format des sprites d'acteurs et accompagnateurs** : Ressources candidates présentes, associations et décodage non
  qualifiés ; bloquant la validation du premier acteur.
- **Couverture française** : Trois lieux de départ et identités établis ; catalogue complet et noms de PNJ à relire par
  entrée native en phases 3/5.
- **Équivalence des variantes** : Tables sauvages distinctes attestées ; géométrie commune et variantes de
  scripts/règles à tester, aucune fusion automatique.
- **Distribution des ressources** : Licence globale absente ; mentions et conditions à résoudre avant distribution. Cela
  n'empêche pas l'audit ni la preuve locale.

La phase 0 est terminée avec ces limites explicitement classées. Elle autorise le prototype de phase 1,
pas la distribution HGSS. Si une ressource manque à ce prototype, nommer son chemin/membre et chercher
une source compatible épinglée ; à défaut, arrêter cette branche sans remplacer par GSC ou Sinnoh.

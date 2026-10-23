# HGSS — règles Android et sauvegardes préparatoires

Les versions 15 et 16 et le groupe 10, `heartgold-soulsilver`, sont reconnus par Android.
La génération reste 4 ; les deux remakes occupent une rangée distincte, de génération d’origine 2.
Le catalogue préparatoire fournit Ho-Oh et Lugia, les couleurs des jaquettes, Johto puis Kanto
et le départ à Bourg Geon. Le choix et sa mémorisation sont testés avec un catalogue en mémoire.
La base distribuée conserve exactement les quatorze jeux actuels : aucun asset n’est activé.
Les guides et objectifs restent à réaliser dans la phase 7. Les outils de reproduction et de bonheur
et les observations d’errants ont leurs règles HGSS ; les tests injectent un catalogue préparatoire.

## Preuve des règles de capture

Source : [pret/pokeheartgold, commit 6988158691eb6178cff697cda0428045ddcba5fb](https://github.com/pret/pokeheartgold/blob/6988158691eb6178cff697cda0428045ddcba5fb/src/battle/battle_command.c),
fonction `BattleSystem_CalculateBallShakes`. La table `sMoonBallPokemon` se trouve dans
`asm/overlay_12_battle_command.s` au même commit. Les sources ont été lues dans le cache épinglé.

`BallContext.versionGroup` distingue HGSS de Sinnoh. Les formules entières de PV, statut et
quatre secousses sont communes ; les modificateurs Noigrumes s’appliquent au taux de l’espèce
avant plafonnement à 255. La Niveau Ball conserve les divisions entières et leurs comparaisons
strictes ; elle ne saute pas les PV/statuts comme en GSC. L’Appât Ball dépend de la pêche,
la Speed Ball de la vitesse de base (au moins 100), et la Love Ball de la même espèce avec
sexes opposés. Sans sexe ne satisfait pas ce dernier critère.

La Lune Ball reconnaît les quatorze espèces de la table native, y compris bébés et évolutions.
La Copain Ball ne change pas le taux. La Masse Ball ajoute 20, 30 ou 40 aux seuils 204,8,
307,2 et 409,6 kg. En dessous, le moteur compare par erreur le taux à 1024 : il retire donc
toujours 20. Un résultat négatif devient 1, mais zéro reste zéro.
Le calculateur présente zéro comme probabilité nulle ; il ne simule pas la division par zéro
du calcul de secousses natif. Les tests distinguent explicitement zéro d’une valeur négative.

Le Parc Safari HGSS propose seulement la Safari Ball et les paliers de prudence 0 à 12,
sans dégâts ni statut. Le concours propose seulement la Compét’Ball (×1,5) et conserve les PV
et statuts. Le Parc des Amis garantit la capture avec sa Parc Ball. Le Grand Marais reste
réservé à Sinnoh ; la Mémoire Ball n’est jamais proposée au lancer ordinaire.
Changer de branche normalise un environnement incompatible vers le combat ordinaire.

Les tests `HgssCatchRateTest`, `HgssModelsTest`, `HgssMapCatalogTest`, `GameViewModelTest` et `PokemonViewModelTest`
couvrent les seuils, conditions, environnements, choix préparatoires et changements de jeu.
Les tests existants GSC/Sinnoh restent exécutés avec la suite Android complète.

## Matrice reproduction et bonheur — 6C

Autorité : même commit HGSS que ci-dessus, lu dans le cache épinglé. Les liens pointent vers
les fichiers natifs, sans emprunter les règles de GSC. `DsBreeding` ne partage que les encens et
les passes d’attaques comparés ; `SinnohBreeding` conserve ses propres règles de Pierre Stase.

| Règle | HGSS et différence avec Sinnoh | Source et tests |
|---|---|---|
| Compatibilité | Groupes communs et sexes opposés, ou un Métamorph ; bébés et groupe Inconnu stériles. | `get_egg.c`, `ComputeCompatibilityBetweenBoxMons` ; `BreedingTest`, `BreedingPartnersTest`. |
| Espèce | Neuf encens, tenus par l’un ou l’autre parent ; Manaphy donne Phione ; familles Nidoran et Lumivole/Muciole. | `get_egg.c`, `Daycare_GetEggSpecies`, `sIncenseMons` ; `HgssBreedingTest`, tests des cas d’usage DS. |
| IV | Trois statistiques distinctes ; chaque objet Pouvoir force son IV parmi ces trois. Deux porteurs donnent deux alternatives, un seul IV forcé. Sinnoh ne bénéficie pas de ces objets. | `get_egg.c`, `InheritIVs`, `Daycare_TryGetForcedInheritedIV`, `SetStatIdToPowerItemStat` ; `HgssBreedingTest`. |
| Nature | Pierre Stase sur n’importe quel parent, indépendamment du sexe. Deux pierres : choix d’un porteur. Test natif `< 0x7FFF`, soit 32 767/65 536, avant recherche bornée de personnalité. | `get_egg.c`, `Daycare_EverstoneCheck`, `GenerateEggPID` ; `HgssBreedingTest`, `HgssBreedingUseCaseTest`, `BreedingViewModelTest`. |
| Langues | Quatre essais supplémentaires de personnalité si langues différentes ; cela peut modifier la nature obtenue. Aucune garantie ni prédiction du tirage final. | `get_egg.c`, `SetBreedEggStats` ; explication française dans `HgssToolsTest`. |
| Attaques et talents | Éclosion niveau 1 ; passes œuf, CT/CS, niveaux communs, puis Électacle avec Ballon Lumière sur un parent. Talent lié à la personnalité, sans héritage direct du talent parental. | `get_egg.c`, `InheritMoves`, `Daycare_LightBallCheck`, `SetBreedEggStats` ; `HgssBreedingTest`, `SinnohToolsTest`. |
| Bonheur initial | Dépend de l’espèce à la capture, 120 à l’éclosion ; valeur saisie manuellement, pas de lecture d’une cartouche. Seuil d’évolution 220, selon les autres conditions de la fiche. | `pokemon.c`, `GetMonBaseStat`, `GetMonEvolution`, et `get_egg.c` ; tests existants des évolutions et textes du calculateur. |
| Gains et pertes | Paliers 0–99, 100–199, 200–255 ; plafonds 0 et 255. Gains : +1 Luxe Ball, +1 lieu de réception de l’œuf, puis Grelot Zen ×1,5 arrondi inférieur. Cet ordre vaut aussi pour les consommables, contrairement à Sinnoh. Aucun bonus aux pertes ni à un gain nul. | `pokemon.c`, `MonApplyFriendshipMod` ; `use_item_on_mon.c`, `DoItemFriendshipMod` ; `HgssFriendshipTest`, `FriendshipViewModelTest`. |
| Soins | Coiffeurs : résultat de base +1, +5 ou +10 ; Nina : +10. Même ordre des bonus. Le calculateur demande le résultat obtenu ; aucun tirage simulé. Super Concours et Club Ruban indisponibles. | `scr_seq_0094_D37R0102.s`, `scr_seq_0738_T01R0201.s`, `scrcmd_party.c`, `ScrCmd_MonAddFriendship` ; `HgssFriendshipTest`. |

Sources principales :
[reproduction](https://github.com/pret/pokeheartgold/blob/6988158691eb6178cff697cda0428045ddcba5fb/src/get_egg.c),
[bonheur](https://github.com/pret/pokeheartgold/blob/6988158691eb6178cff697cda0428045ddcba5fb/src/pokemon.c),
[consommables](https://github.com/pret/pokeheartgold/blob/6988158691eb6178cff697cda0428045ddcba5fb/src/use_item_on_mon.c),
[bonus de scripts](https://github.com/pret/pokeheartgold/blob/6988158691eb6178cff697cda0428045ddcba5fb/src/scrcmd_party.c).
Les empreintes normalisées des fichiers lus sont conservées dans `regles-android-hgss-sources.json`.

Les tests de cas d’usage HGSS utilisent des DAO en mémoire pour vérifier les requêtes du groupe 10
et l’identité des deux cartouches ; ils ne prétendent pas charger une base HGSS déjà distribuée.
Les tests de ViewModel couvrent aussi contenu vide, erreur, reprise et changement de jeu.

## Base, collection et export commun — 6D

Le schéma SQL/Room reste **23** : ces règles et le suivi utilisateur n’ajoutent aucune table.
La collection et les observations sont dans DataStore, hors de la base documentaire remplacée.
`PokedexSchemaTest` contrôle l’alignement de l’asset versionné et de Room. Aucune régénération
ni activation des remakes n’est nécessaire pour ce lot ; la base candidate contenant leurs données
reste la sortie de 8A, puis son activation relève de 8B.

Chaque installation ouvre `pokedex-<lastUpdateTime>.db` depuis l’asset. Les anciennes copies ne sont
retirées qu’après ouverture réussie. `DataModuleTest` simule deux dates d’installation, rouvre l’asset
et vérifie que captures GSC/HGSS, Zarbi, guides et observations restent identiques dans le DataStore réel.
Ce test JVM ne remplace pas une installation ADB sur téléphone (recette de 8C).

Le format commun reste `pokmaps-collection`, schéma JSON **1**. Les champs `favorites`, `caught`,
`completed`, `unown` et `forms` sont inchangés. Pour chaque entrée de `games` :

- Sinnoh conserve `sinnohRoamers` en lecture **et** en écriture, compatible avec ses exports historiques.
- HGSS écrit et lit `roamerObservations`, une table espèce → identifiant de route.
- `roamers` reste une liste vide pour les anciens lecteurs ; les anciens relevés GSC abandonnés restent ignorés.
- L’absence des champs optionnels vaut collection vide. La fusion unit captures, formes et étapes,
  conserve les cartouches absentes de l’import et remplace seulement les observations importées du même errant.
- Un import invalide est refusé avant toute écriture : version absente du catalogue, espèce hors génération,
  forme inconnue, doublon ou route incompatible. Aucun report automatique de GSC vers HGSS.

Les préférences conservent la clé historique `sinnoh_roamers_<version>` pour les deux familles :
ce nom interne n’impose aucune migration et chaque cartouche garde sa propre clé.

Les tables de `field_roamer.c` prouvent les listes : Raikou et Entei niveau 40 sur les 16 routes de Johto
(29–39 et 42–46), Latias dans HeartGold ou Latios dans SoulSilver niveau 35 sur les 25 routes de Kanto
(1–22, 24, 26, 28). Suicune n’est pas errant. Les observations ne prédisent aucun déplacement.
[Source native](https://github.com/pret/pokeheartgold/blob/6988158691eb6178cff697cda0428045ddcba5fb/src/field_roamer.c).

`HgssBackupTest` couvre le document commun, l’import historique via `CollectionBackupUseCase`,
la fusion sans perte et le refus atomique d’une mauvaise route. `HgssCollectionUseCaseTest` vérifie
captures et formes indépendantes, favoris communs et partage explicite par génération/tous jeux.
`HgssRoamersTest` et les tests historiques Sinnoh contrôlent espèces, niveaux, régions et routes.

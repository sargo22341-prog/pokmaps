# HGSS — identité Android et capture préparatoires

Les versions 15 et 16 et le groupe 10, `heartgold-soulsilver`, sont reconnus par Android.
La génération reste 4 ; les deux remakes occupent une rangée distincte, de génération d’origine 2.
Le catalogue préparatoire fournit Ho-Oh et Lugia, les couleurs des jaquettes, Johto puis Kanto
et le départ à Bourg Geon. Le choix et sa mémorisation sont testés avec un catalogue en mémoire.
La base distribuée conserve exactement les quatorze jeux actuels : aucun asset n’est activé.
Les guides, objectifs, errants et outils de bonheur/reproduction des étapes suivantes ne sont pas
empruntés à GSC ou Sinnoh ; leurs points d’entrée spécifiques restent explicitement indisponibles.

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

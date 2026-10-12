# Bilan avant la génération 4

Bilan du 12 octobre 2026. Onze jeux sont distribués, avec deux branches GBA distinctes.
Ce bilan décrit la portée des données et des contrôles ; il ne certifie pas chaque état de scénario.

## Acquis

Les assets finaux sont versionnés et inventoriés : base Room/SQLite, tuiles WebP, sprites normaux
et chromatiques des espèces 1 à 386, personnages, offres et contenus de Hoenn.
La CI et la publication utilisent ces fichiers sans génération ni téléchargement de contenu Pokémon.
Le workflow manuel du pipeline mesure génération, cache, assets et APK debug ; il ne publie rien.

Les Pokédex régional et National, capture GBA, talents, formes, reproduction, bonheur, collections,
guides et errants disposent de tests JVM. Les tests ordinaires Python fonctionnent sans sources brutes ;
les tests pipeline vérifient explicitement les sources épinglées et la reproduction des sorties.
Les anciennes sauvegardes JSON de schéma 1 restent importables, avec fusion des collections.

## Limites explicites

- Les distributions externes exigent un événement extérieur ; elles sont exclues des collections ordinaires.
- Les cartes sont statiques : ni sauvegarde de cartouche, ni déplacement de PNJ, ni tirage aléatoire simulé.
- Les rencontres des installations de combat sont listées, sans simulation de leurs parcours aléatoires.
- La Baie Enigma personnalisée et les saveurs aléatoires du bloc noir restent indéterminées.
- Les petits terrains gardent six avertissements de capacité à Hoenn et quatorze dans les remakes,
  détaillés dans les bilans de rencontres ; aucun placement supplémentaire artificiel n'est inventé.
- Le calculateur de capture exclut le Parc Safari et estime l'IV des PV ; les défauts du moteur sont conservés.
- La dépréciation AGP `Configuration.setVisible(boolean)` reste visible, sans exclusion.

La relecture finale et les mesures de cette passe sont consignées dans la phase 9 du
[plan](../plan_gen_3.md). Les contrôles automatisés complètent les essais visuels ; ils ne remplacent
pas une vérification de chaque intérieur et de chaque branche des scripts.


La base `pokedex.db` dépasse 5 Mio : 8 884 224 octets (8,47 Mio), pour les tables et index
des onze jeux. C’est le seul asset unitaire au-dessus de ce seuil ; les images restent en tuiles.

## Avant d'intégrer Sinnoh

Partir d'un jeu dans `GAMES_IN_PROGRESS`, épingler ses sources, choisir sa famille de cartes et
valider le format Nintendo DS. Ne pas réutiliser les attributs GBA par supposition.
La séparation physique/spéciale dépendra de l'attaque ; les évolutions, objets et règles de reproduction
devront être relus par jeu. Les sprites Noir/Blanc couvrent encore 387 à 493.
Les archives RetroAchievements des générations 4 et 5 sont préparatoires ; elles n'activent aucun jeu.
HeartGold/SoulSilver devront constituer une branche distincte de Diamant/Perle/Platine.

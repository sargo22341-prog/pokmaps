# Ajouter une génération

Les générations 1 à 4 sont distribuées, jusqu'à Diamant, Perle et Platine.
Les archives de succès futurs ne constituent pas une activation.

Avant toute nouvelle branche DS, valider **un premier lieu complet**, sans ROM : image 2D hors ligne,
coordonnées des cases, étages, collisions, passages et génération reproductible.
Les cartes de `pokeplatinum` et `pokediamond` sont produites et validées depuis les modèles, textures,
matrices, événements et scripts épinglés, puis distribuées en tuiles hors ligne pour MapCompose.
Cette validation ne vaut pas pour les cartes de HeartGold/SoulSilver, la prochaine branche envisagée.

`Generation`, `GameVersion` et `VersionGroup` exigent des règles explicites par jeu.
HeartGold/SoulSilver formeront une branche distincte de Diamant/Perle/Platine.
Les formes, événements externes et succès ont des modèles et sources éditoriales dédiés ;
leur existence ne valide pas les règles d’une nouvelle branche. L’index des mentions de guides est conservé
pour Sinnoh après mesure sur son catalogue DS ; refaire cette mesure avec le catalogue de la nouvelle branche
avant de décider de le remplacer.

À chaque intégration, tester les changements de famille de cartes, les états vide et erreur, les captures
et la sauvegarde avec les anciens jeux. Les essais sur émulateur gardent des captures ; l'installation
sur téléphone utilise `adb install -r -d`, sans effacement, avec comparaison des préférences avant/après.
La séparation physique/spéciale par attaque est gérée en génération 4. Points suivants à décider :
talents cachés en 5, type Fée et taux chromatique en 6, formes régionales et mécaniques propres aux jeux suivants.
Les sprites actuels couvrent une source jusqu’à l’espèce 649 ; au-delà, choisir et valider une nouvelle source.
La [procédure d’ajout](../donnees/pipeline.md#ajouter-un-jeu) précise les fichiers et contrôles concernés.

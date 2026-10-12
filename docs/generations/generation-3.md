# Génération 3 et Remake 1G

Rubis, Saphir et Émeraude constituent la branche Hoenn ; Rouge Feu et Vert Feuille constituent
la branche Remake 1G. Les cinq jeux sont distribués hors ligne, avec les six jeux précédents.
Le moteur GBA commun ne rend pas leurs cartes, scénarios ou règles interchangeables.

| Branche | Cartes | Pokédex | Sources pret |
|---|---|---|---|
| Hoenn | Hoenn, Plongée, marées, îles événementielles | Hoenn 202, National 386 | pokeruby, pokeemerald |
| Remake 1G | Kanto, Îles Sevii, îles événementielles | Kanto 151, National 386 | pokefirered |

Les commits sont épinglés dans `tools/pokemaps_data/sources.py`. Les rencontres sauvages viennent
de `wild_encounters.json`, avec les probabilités du moteur ; PokéAPI complète noms, Pokédex et données Pokémon.
Les coordonnées, conditions des personnages, équipes et revanches sont lues dans pret et corrigées
explicitement dans les CSV éditoriaux. Room et la base générée partagent le schéma 15.

## Fonctionnalités

Le choix du jeu sépare la ligne Hoenn de « Remake 1G ». Les fiches proposent talents, objets tenus,
attaques et évolutions par jeu, Deoxys dans sa forme propre et les quatre formes de Morphéo.
Le calculateur GBA reproduit les contrôles entiers et les nouvelles Balls ; le Parc Safari est exclu.
Les remakes proposent le suivi des 28 Zarbi ; Hoenn ne propose pas de collection de formes.

Les guides comprennent douze chapitres par branche, quêtes, astuces, bugs et 484 succès officiels GBA
traduits. Les outils de reproduction utilisent les IV, objets et règles de transmission de chaque jeu.
Les collections excluent échanges et événements externes et respectent les choix incompatibles.
Le suivi des errants mémorise une observation manuelle par cartouche ; aucune sauvegarde du jeu n'est lue.
Hoenn ajoute baies, Concours, recettes de Pokéblocs et 120 décorations dans le catalogue `hoenn.json`.

## Lectures détaillées

- Cartes : [Hoenn](cartes-hoenn.md), [Remake 1G](cartes-remake-1g.md).
- Rencontres : [socle commun](rencontres-gen3-communs.md), [Hoenn](rencontres-hoenn.md),
  [Remake 1G](rencontres-remake-1g.md).
- Personnages : [socle commun](personnages-gen3-communs.md), [services Hoenn](services-hoenn.md),
  [services Remake 1G](services-remake-1g.md).
- [Guides et outils](guides-gen3.md), [contenus Hoenn](contenus-hoenn.md).
- [Bilan avant la génération 4](bilan-generations-1-2-3.md), [plan et contrôles](../plan_gen_3.md).

Les distributions externes sont signalées, sans être comptées comme obtention ordinaire.
Les cartes de la Zone de Combat sont affichées ; les contenus aléatoires ne sont pas simulés.
Les séries de rencontres de la Pyramide et du Reptile sont conservées hors ligne.
La Baie Enigma personnalisée, les tirages de cartouche, les motifs de Spinda et les futurs déplacements
des errants ne sont pas prédits. Les limites de placement des petits terrains sont documentées
dans les bilans de rencontres, séparément pour chaque branche.

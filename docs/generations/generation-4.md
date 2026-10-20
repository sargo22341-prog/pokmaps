# Génération 4 — Diamant, Perle et Platine

Les trois jeux de Sinnoh sont distribués hors ligne, avec les onze jeux précédents.
HeartGold et SoulSilver constituent une prochaine branche distincte.

| Jeux | Famille de cartes | Pokédex Sinnoh / National |
|---|---|---|
| Diamant, Perle | `diamond-pearl` | 151 / 493 |
| Platine | `platinum` | 210 / 493 |

Les identifiants de version sont 12, 13 et 14. Les deux moteurs pret sont lus séparément :
les données communes sont comparées par les tests de sources, les différences restent propres au jeu.
La séparation physique/spéciale dépend de chaque attaque. Les évolutions conservent sexe, heure,
objet, attaque connue, espèce dans l'équipe et proximité d'un lieu particulier.

## Références techniques par sujet

| Modification | Référence |
|---|---|
| Matrices, rendu oblique, étages, assemblages et passages | [Cartes DS](cartes-sinnoh.md) |
| Horaires, conditions, rencontres spéciales et probabilités | [Rencontres DS](rencontres-sinnoh.md) |
| Scripts, équipes, revanches, objets et déblocage du National | [Personnages DS](personnages-sinnoh.md) |
| Dons, boutiques, échanges, tuteurs et paiements | [Services DS](services-sinnoh.md) |
| Soluces, objectifs, calendrier, outils et succès | [Guides DS](guides-sinnoh.md) |
| Baies, Poffins, Super Concours, Souterrain et combat | [Contenus de Sinnoh](contenus-sinnoh.md) |

Les [sources et commandes](../donnees/pipeline.md) décrivent la génération et ses aperçus.
Les [contrôles](../developpement.md) couvrent Android, les assets versionnés et les sources épinglées.

## Comportement et limites

La carte propose matin, jour et nuit, les étages et les niveaux superposés. Changer de famille revient
au départ de la nouvelle carte ; Diamant et Perle partagent leur famille, Platine possède la sienne.
Le Pokédex propose Sinnoh et National ; captures, formes, Zarbi et observations des errants sont
conservés par les préférences et la sauvegarde JSON, compatible avec les anciens exports.

Le calculateur de capture applique les règles DS, dont Sombre, Soin et Rapide Ball, le Grand Marais
et le Parc des Amis. La Mémoire Ball est réservée aux distributions. Les formes disponibles suivent
la cartouche ; les formes Fée et ??? d'Arceus ne sont pas proposées.

Les possibilités aléatoires sont documentées sans lecture de sauvegarde ni prédiction : arbres à Miel,
Barpau, Grand Marais, Jardin Trophée, essaims, errants et installations de combat.
Les événements externes et transferts sont indiqués et exclus des objectifs ordinaires.
Le décor garde son état initial : mécanismes d'Arènes, textures à l'image zéro et Villa vide.
Le Monde Distorsion présente ses plans et liaisons sans simulation de gravité ou de plateformes mobiles.
Les mini-jeux de concours, Poffins et fouilles ne sont pas simulés.

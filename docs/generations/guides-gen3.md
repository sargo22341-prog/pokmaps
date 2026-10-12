# Guides GBA — fin de phase 7

Les cinq bibliothèques ajoutent les 484 succès officiels exportés le 12 octobre 2026,
avec conditions en français, points, mentions manquables et liens vers leurs chapitres.
Les 519 succès des six anciens jeux sont conservés. Hoenn propose 26 articles originaux par
jeu ; chaque remake en propose 20. La synchronisation manuelle RetroAchievements parcourt
les onze identifiants officiels ; aucune requête n’est déclenchée par le chargement des guides.

Les archives publiques des générations 1 à 5 et les traductions GBA sont dans
[`tools/data/retroachievements`](../../tools/data/retroachievements/README.md).
Les ensembles suivants sont disponibles pour une intégration future sans nouvelle lecture authentifiée.
La clé utilisée pour l’export n’est pas enregistrée. L’option facultative de synchronisation de
la progression d’un joueur conserve son fonctionnement et nécessite ses propres identifiants.

## Collections

Deux articles par jeu proposent le Pokédex régional et le National accessibles sans échange
externe, distribution ni duplication. `Gen3CaptureGoals` expose les ensembles d’espèces et
les choix exclusifs, puis projette les mêmes règles dans le régional.

| Version | National accessible | Objectif officiel associé |
|---|---:|---:|
| Rubis | 177 | 91998 |
| Saphir | 178 | aucun dans l’ensemble officiel |
| Émeraude | 212 | 57275 |
| Rouge Feu | 170 | 33625 |
| Vert Feuille | 171 | 34809 |

Les espèces proviennent des rencontres de la base distribuée, complétées par leurs évolutions
possibles et pré-évolutions obtenues par reproduction. Les évolutions par échange et les
événements externes sont exclus. Les starters de Hoenn forment un choix de trois espèces ;
les fossiles Lilia/Anorith sont exclusifs dans Rubis/Saphir, disponibles ensemble dans Émeraude.
Rubis et Émeraude ont une seule Pierre Lune pour Grodoudou ou Delcatty ; les Lunatone de
Saphir permettent d’en obtenir d’autres. Kecleon n’est pas un choix exclusif.
Les partenaires de Johto offerts dans Émeraude exigent les 200 espèces ordinaires de Hoenn :
ils ne sont pas accessibles sans échanges et restent exclus de ce compteur.

Dans les remakes, le partenaire et sa bête errante constituent un choix corrélé de quatre espèces :
Bulbizarre/Herbizarre/Florizarre + Entei, Salamèche/Reptincel/Dracaufeu + Suicune,
Carapuce/Carabaffe/Tortank + Raikou. Les fossiles de Kanto restent exclusifs.
La reproduction de Debugant permet les deux combattants du Dojo et Kapoera ; celle d’Évoli
permet Aquali, Voltali et Pyroli. Mentali et Noctali nécessitent une horloge absente des remakes.
Les Ruines Tanoby suivent 28 formes de Zarbi dans leur quête originale : aucun identifiant
de succès Zarbi n’est ajouté, car les ensembles officiels GBA n’en proposent pas.
Le compteur de Johto reste à 26 formes.

## Errants

L’accueil des guides permet de mémoriser une dernière route observée, d’ouvrir la carte et
d’effacer l’observation. Ce suivi manuel n’interprète aucune sauvegarde et ne prédit aucun déplacement.

- Or/Argent : trois bêtes ; Cristal : Raikou et Entei, Suicune suivant le scénario.
- Rubis : Latios ; Saphir : Latias ; Émeraude : Latias si rouge, Latios si bleu à la télévision.
- Rouge Feu/Vert Feuille : une bête suivant le partenaire, sur les routes 1 à 25 de Kanto,
  avec seulement la partie nord de la Route 21.
- Hoenn : routes 110, 111 et 117 à 134, suivant les tables du moteur.

Chaque cartouche GBA ne conserve qu’une observation. Un import remplace le choix précédent
au lieu de réunir deux errants impossibles sur une même partie. Les anciennes observations
de Johto restent séparées par espèce. Les routes sont validées contre le catalogue de chaque jeu.

Sources des règles : `src/roamer.c` et les données Pokémon des dépôts pret épinglés :
`pokeruby` à `5784633ce4ef`, `pokeemerald` à `731ad5bfd6e6`, `pokefirered` à `037335f4c725`.
Les noms de cartes propres à chaque branche sont validés contre `pokedex.db`.
Les compteurs ne prouvent pas les autres restrictions d’un succès ; son texte complet fait foi.

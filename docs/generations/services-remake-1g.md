# Services de Rouge Feu et Vert Feuille

Les sources pret épinglées de `pokefirered` alimentent le catalogue préparatoire
`character_curation.json`, généré par `--gen3-curation-only`. Les jeux restent en cours
d'intégration ; l'assemblage Room et l'affichage Android relèvent de la phase 6.

| Lieu | Contenu conservé |
|---|---|
| Laboratoire de Cramois'Île | Amonita, Kabuto et Ptéra au niveau 5, avec leur fossile requis |
| Pension de l'Île 4 | Deux parents, œuf et retrait à 100 ₽ plus 100 ₽ par niveau gagné |
| Casino de Céladopole | Cinq Pokémon par version, cinq CT et cinq objets, tarifs en jetons |
| Guichet du Casino | 50 jetons pour 1 000 ₽ ou 500 pour 10 000 ₽ ; dons gratuits distincts |
| Tuteurs | Capacités et drapeaux d'utilisation unique conservés dans les chemins des scripts |
| Effaceur de Parmanie | Service d'effacement des capacités |
| Centre Pokémon de Carmin sur Mer | Don du Cherche VS, recharge après 100 pas |

Les fossiles demandent de quitter le laboratoire puis de revenir. Leur objet requis est distinct
d'un objet tenu. Les œufs de la Pension dépendent des parents et ne sont pas des dons d'espèce fixe.

Les lots Pokémon diffèrent selon la version :

| Pokémon | Rouge Feu : jetons / niveau | Vert Feuille : jetons / niveau |
|---|---|---|
| Abra | 180 / 9 | 120 / 7 |
| Mélofée | 500 / 8 | 750 / 12 |
| Minidraco | 2 800 / 18 | 4 600 / 24 |
| Insécateur | 5 500 / 25 | — |
| Scarabrute | — | 2 500 / 18 |
| Porygon | 9 999 / 26 | 6 500 / 18 |

`pret_remake_services.py` lit le prix résolu de `VAR_TEMP_2` pour les lots et les instructions
`removemoney` pour les jetons. Un prix illisible arrête l'export. Les coordonnées, provenance,
versions et conditions de scénario restent celles des scripts. Les équipes et conditions des
revanches du Cherche VS sont déjà conservées par le catalogue des dresseurs.

Les tests en mémoire distinguent achat et don de jetons et refusent un coût inconnu. Les tests
sur sources épinglées vérifient les fossiles, les dix lots d'objets, les cinq lots Pokémon de
chaque version, la Pension, un tuteur unique, l'Effaceur et le don du Cherche VS.

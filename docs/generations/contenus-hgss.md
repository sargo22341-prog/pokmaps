# Guides et activités HeartGold / SoulSilver

Les sorties de 7A à 7E alimentent désormais les jeux distribués. La génération complète exporte
`hgss.json` et `strings_guides_hgss.xml` ; les commandes ciblées ci-dessous restent dédiées à la relecture.
Le [catalogue versionné](contenus-hgss-catalogue.json) se consulte sans cache ni réseau.
Les textes éditoriaux français résident dans `tools/data/hgss_guides.json`, `hgss_calendar.json`
et `hgss_activities.json` ; ils ne sont pas repris des soluces GSC.

## Génération et relecture

Après les aperçus de rencontres et de personnages validés :

```powershell
python tools/build_data.py --hgss-content-only
python tools/check_assets.py --hgss-content tools/build/preview/hgss-content
python -m pytest -q -c tools/pyproject.toml tools/tests/test_hgss_content.py
python -m pytest -q -c tools/pyproject.toml -m pipeline tools/tests/test_hgss_content_sources.py
```

Ouvrir `tools/build/preview/hgss-content/index.html` pour relire les deux parcours, les choix de starters,
les activités et le calendrier. Les données détaillées sont dans le `content.json` voisin.
La page fonctionne sans serveur, JavaScript ni ressource distante.
La génération valide le staging avant de remplacer l'aperçu existant ; un échec conserve celui-ci.
Les inventaires des rencontres et personnages, leurs recettes et leurs propres prérequis sont vérifiés.
Avec le dossier d'aperçu par défaut, la génération actualise aussi le catalogue versionné et sa
[preuve d'intégrité](contenus-hgss-preuve.json). Un `--preview` personnalisé reste isolé de ces sorties versionnées.

Le [contrat des sources](contenus-hgss-sources.json) épingle les fichiers natifs supplémentaires au commit HGSS
déjà qualifié. Le catalogue Pokémon est relu depuis les sources HGSS et PokéAPI vérifiées de la phase 3.
Les identifiants de lieux, acteurs et offres proviennent des catalogues HGSS, jamais de GSC ou de Sinnoh.

## Soluces et liens

Chaque version possède 41 entrées : Johto, Kanto, après-Red et quêtes annexes.
Les étapes ont des identifiants stables et des prérequis acycliques ; l'ordre proposé à Kanto
est un parcours possible, sans imposer un ordre inexistant aux Arènes indépendantes.
La branche des Kimono conduit à Ho-Oh dans HeartGold et à Lugia dans SoulSilver.
Le parcours va jusqu'à Red, aux starters supplémentaires et à la Tour Enfouie.

Chaque entrée relie ses lieux français aux en-têtes natifs, les personnages à leurs événements,
les objets remis aux identifiants des offres et les preuves aux scripts.
Les liens désignent le contexte du lieu ; ils ne déclarent pas que tous ses personnages ou cadeaux
sont disponibles à la même étape. Les conditions restent celles du catalogue des personnages.
Les écrans Android proposent 334 guides par cartouche, avant les 136 succès : parcours,
54 objectifs, calendrier, configurations Safari et Pokéwalker, Zone de Combat et services de scène.

## Objectifs par cartouche

Un objectif est une collection réalisable après Red sur une seule sauvegarde, avec les choix de starters
fixés : trois choix Johto × trois choix Kanto × trois choix Hoenn, soit 27 configurations par version.
Chaque configuration contient le régional, le National et le complément des 493 espèces,
avec une explication par espèce exclue. Additionner plusieurs configurations créerait un objectif impossible.

Le calcul part des banques sauvages rattachées à des lieux, des arbres, du concours, du Safari et des
obtentions locales. Le Safari cherche les configurations minimales nécessaires aux candidats pour chacun
des 26 états distincts de maturation : trente objets au maximum, ordre des remplacements respecté.
La présence d'un candidat dans une table ne suffit pas à le compter.
Une fermeture bornée ajoute les évolutions locales, la reproduction avec Métamorph et les échanges PNJ
dont la contrepartie est accessible. Les échanges non appelés par les scripts sont écartés.
Les espèces d'une autre provenance locale restent comptées même si une provenance externe existe aussi.

Les exclusions distinguent notamment :

- les deux autres starters de chaque trio et leurs lignées ;
- les évolutions par échange, par lieu absent ou par beauté préparée ailleurs ;
- les accessoires, transferts, échanges externes et distributions ;
- les fossiles importés : HeartGold fournit Amonita, Anorith et Ptéra ; SoulSilver, Kabuto, Lilia et Ptéra ;
- Latias dans HeartGold et Latios dans SoulSilver, avec Mystécristal externe pour l'autre ;
- Kyogre dans HeartGold, Groudon dans SoulSilver et Rayquaza qui nécessite les deux provenances HGSS.

Les probabilités, horaires, essaims et jours restent conditionnels. Il ne s'agit ni d'une lecture de sauvegarde,
ni d'une prédiction de la disponibilité du jour. Les configurations sont collectables au fil du temps.

## Activités et calendrier

| Activité | Données conservées |
|---|---|
| Pokéathlon | Stocks quotidiens avant/après National, prix, limites, Cartes Mémo et tables des parcours. |
| Noigrumes | 31 arbres, sept conversions de Fargas, quantités et remise au changement de jour. |
| Noigrumes à boire | Sept contributions sur cinq axes, provenance et préparation ; sans simulation des performances. |
| Safari | Douze habitats, cinq méthodes, trois horaires, exigences de blocs et règles de maturation. |
| Pokéwalker | 27 parcours : six candidats, dix objets, capacités, niveaux, seuils, poids et accès. |
| Concours | Six configurations jour/National avec niveaux et probabilités conditionnelles. |
| Pokématos | Enregistrement, créneaux et destinations des revanches, dont les seize Champions. |
| Radio | Sons de Hoenn/Sinnoh, essaims et conditions de déblocage. |
| Photos | Sites, coordonnées et paramètres natifs ; album de 36 photos. |
| Voltorbataille | 80 configurations, niveaux et gains possibles, sans prédire le plateau. |
| Baies et événements | Guides des pots, obtentions externes et exclusions. |

Les deux premiers parcours Pokéwalker sont ouverts au départ ; les vingt premiers utilisent les Watts cumulés,
avec le National à partir du neuvième. Les sept derniers restent classés comme accès externes avec accessoire.
Les groupes A/B/C, candidats et poids restent séparés : aucun taux global inventé.
Les noms natifs des tables servent à la traçabilité, sans être présentés comme des traductions françaises officielles.

Le calendrier ajoute aux contacts les concours, Lokhlass du vendredi, la danse des Mélofée,
les voyages réguliers de l'Aquaria, la radio, les prix du Pokéathlon et les renouvellements quotidiens.
Les jours structurés suivent la convention Python : lundi = 0, dimanche = 6.

## Zone de Combat — 7D

Le catalogue et la page hors ligne comprennent les cinq installations, les formats, conditions,
Photos Argent/Or et réserves possibles. La Tour, l’Usine, le Castel et l’Arcade ont des séries de sept combats ;
la Scène, dix. Les meneurs interviennent en Simple aux combats 21/49, sauf Célosia aux combats 50/170.
Les Photos restent distinctes de l’étoile obtenue après 100 victoires à la Tour.
Les noms et Photos ont aussi été recoupés dans les pages [Scène de Combat](https://www.pokepedia.fr/Sc%C3%A8ne_de_Combat)
et [Photo](https://www.pokepedia.fr/Photo) ; les règles et nombres proviennent du moteur HGSS épinglé.

Le [contrat de comparaison](combat-hgss-sources.json) conserve les empreintes des archives HGSS,
des sélecteurs et du catalogue Platine versionné `sinnoh.json`. Chaque génération relit indépendamment HGSS :
950 configurations utiles, 315 réserves de dresseurs, 477 configurations de la Scène et dix rangs.
Les entrées zéro des archives Pokémon sont des sentinelles et ne deviennent pas des équipes.
La génération refuse le réemploi si une configuration, réserve, plage ou rang censé être commun diffère.
Les traductions des configurations égales sont alors reprises du catalogue Platine.

Les huit séries ordinaires de l’Usine sont communes, avec des réserves distinctes pour les locations
et les adversaires en niveau libre. Trois entrées natives diffèrent de Platine :

| Table | Entrée | HGSS | Platine |
|---|---|---|---|
| Niveau 50 | Cardus Or | 759–950 | 351–486 |
| Libre, adversaires | Cardus Argent | 351–486 | 759–950 |
| Libre, locations | Entrée 9, inutilisée par le sélecteur borné aux huit séries | 351–486 | 759–950 |

Ces entrées restent lues dans HGSS. Les réserves de Cardus remplacent les entrées vides de l’archive des dresseurs ;
Célosia relève du sélecteur propre à la Scène. Une réserve décrit des candidats, jamais une équipe garantie.
Le moteur de la Tour inclut sa borne supérieure ; ceux de l’Usine, du Castel et de l’Arcade l’excluent.
Les types, rangs, objets, formes, capacités et masques EV restent conservés. Aucun tirage n’est simulé.

Les récompenses comprennent les tables de Points Combat de la Tour, les 20 points après Koner,
les Photos et les 42 lots du comptoir avec leurs prix HGSS. Les Points Castel gardent leur usage propre.
Le script du PP Plus vérifie une place de 48 dans le Sac, mais remet **un** objet : le catalogue distingue
ce contrôle de la quantité remise. Les services Wi-Fi sont décrits comme historiques.

## Succès — 7E

Les 136 entrées de `tools/data/retroachievements/7212.json` sont traduites dans `hgss_fr.csv` :
titres descriptifs, conditions, points, identifiants officiels et caractère manquable.
L’archive publique du 12 octobre 2026 est conservée intacte, avec ses empreintes ; aucun nouvel export réseau.
Les seuils officiels 373/371 du National sont ceux du set, distincts des objectifs « cartouche seule » de 7B.
Les conditions de niveau, style Défini, session unique, Master Ball et événements externes restent explicites.
Deux descriptions officielles renvoient aux commentaires du service (cadeaux et fonds de PC) :
ce renvoi est signalé comme tel ; ces commentaires ne figurent pas dans l’archive locale.

La page de relecture affiche toutes les entrées sans serveur ni réseau.
`python tools/build_data.py --achievement-resources-only` génère les ressources Android :
une définition par succès dans `strings_achievements_15.xml`, avec une liste référençant ces mêmes définitions
pour la version 16. Les deux listes sont vérifiées depuis les ressources Android compilées.
Les deux cartouches utilisent **7212** ; l’archive SoulSilver **39076**, vide, n’est jamais synchronisée.
La synchronisation manuelle lit une fois chaque ensemble distinct, puis associe séparément aux versions 15 et 16
les déverrouillages ordinaires et hardcore. Un échec ne sauvegarde aucune progression partielle.
La connexion et l’observation des préférences ne déclenchent aucune lecture réseau.

Le schéma Room 23 est conservé. La candidate vérifie que les lignes et fichiers des quatorze jeux antérieurs
sont identiques avant l’activation des deux remakes.

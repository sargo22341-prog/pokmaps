# Guides et succès

Les bibliothèques regroupent soluces, quêtes annexes, astuces et bugs, ainsi que les succès officiels
traduits pour les générations 1 à 4.
Les étapes cochées et captures restent locales ; les textes ne lisent pas la sauvegarde du jeu.
Les sources des succès sont les [archives et CSV français](../../tools/data/retroachievements/README.md).

Sans connexion RetroAchievements, les cases et compteurs suivent les validations manuelles.
Avec une connexion, seuls les succès synchronisés et leur compteur sont affichés ; les coches manuelles
restent conservées pour une déconnexion ultérieure. La synchronisation se lance uniquement dans les Réglages.

Les objectifs de collection excluent échanges et événements externes et comptent les choix incompatibles
par alternative : starters, fossiles et autres ressources limitées. À Sinnoh, deux objectifs distincts
utilisent le régional de la version puis le National, jusqu’à l’après-Ligue. Ils excluent aussi les interactions
multijoueurs, les transferts et la double insertion GBA. Platine compte une seule famille de fossile de Sinnoh,
selon la parité de l’identifiant du dresseur ; les anciens fossiles restent renouvelables.
Ces compteurs ne prouvent pas le respect des autres
restrictions d’un succès. Les jeux GBA n’ajoutent pas de quête de collection doublant le compteur du Pokédex.
Les quêtes de Zarbi partagent le compteur des formes : 26 à Johto, 28 dans les remakes.
Les errants sont présentés par condition, niveau et région. À Sinnoh, une dernière route observée peut être
notée pour chaque errant : deux dans Diamant/Perle, cinq dans Platine. Le relevé reste propre à la cartouche
et se corrige ou s’efface dans le guide ; il ne prédit aucun déplacement.
Les règles GBA détaillées sont dans [guides-gen3.md](../generations/guides-gen3.md).

Sinnoh propose 12 chapitres de soluce par jeu, des quêtes annexes, des conseils et des bugs documentés.
Les textes distinguent l’ordre des Arènes, les CS, les rencontres et l’après-Ligue de Diamant/Perle et de Platine.
Le calendrier décrit les périodes horaires, Baudrive le vendredi, les activités quotidiennes et les revanches
du rival le week-end. Il ne simule aucun tirage et suit l’horloge de la console, sans la modifier.
Les succès de Diamant (121), Perle (210) et Platine (101) sont traduits depuis les archives locales,
avec leurs conditions complètes, points, restrictions et liens vers les chapitres concernés.

## Reproduction et bonheur

Disponibles dans Guides → Astuces à Johto, dans les jeux GBA et à Sinnoh. Le choix des parents filtre
les partenaires compatibles
(groupes d’œufs, sexe, Métamorph, espèces stériles) et affiche le bébé et les attaques transmises.
Johto utilise les DV ; les jeux GBA utilisent six IV, les objets tenus et les règles propres à chaque cartouche.
Émeraude applique notamment Pierre Stase à la femelle ou Métamorph prioritaire, et Ballon Lumière pour Électacle.
Les résultats décrivent les possibilités, sans prédire un œuf. Le bonheur applique les bonus du jeu :
Grelot Zen, Luxe Ball, lieu de rencontre, baies d’Émeraude et massage des remakes selon leur disponibilité.

À Sinnoh, les neuf Encens sélectionnent le bébé ou sa forme adulte ; Manaphy produit Phione.
Les œufs éclosent au niveau 1. La Pierre Stase concerne la mère ou Métamorph ; des parents de langues
différentes ne garantissent pas cet effet. Les objets Pouvoir et le Nœud Destin ne transmettent pas d’IV.
Le moteur peut répéter un choix de statistique parmi ses trois transmissions : un à trois IV distincts
sont hérités. L’outil ne prédit aucun IV.
Le bonheur distingue les événements du moteur, les objets et les services. Le massage de
Voilaroc donne +3 ; le soin du Club Ruban donne +5, +10 ou +30 selon le tirage (70 %, 25 %, 5 %).
Le Grelot Zen précède les bonus de Ball et de lieu pour les objets et ces services ; il les suit pour
les autres événements du moteur. Les trois issues sont proposées sans simuler le hasard.
Les coiffeurs de Johto ne sont pas proposés.

## Modifier un guide

- Définitions dans `data/guide/`, textes français dans `res/values/strings_guides*.xml`.
- Succès : modifier archives/traductions, puis produire les ressources avec
  `python tools/build_data.py --achievement-resources-only`. Ne pas éditer les sorties à la main.
- Liens explicites : `[[pokemon:25|Pikachu]]`, `[[place:route-1|Route 1]]`, `[[item:potion|Potion]]`,
  `[[character:oaks-lab:Prof. Chen|Professeur Chen]]`. Les noms reconnus dans la base deviennent aussi des liens.
- `GuideRepositoryTest` charge les quatorze bibliothèques et vérifie les liens ainsi que les succès déjà intégrés
  contre la base distribuée. Les sources éditoriales de Sinnoh sont nommées par jeu et fixées aux commits pret.

Les fournisseurs sont choisis par branche avant construction ; seuls les succès du jeu choisi sont construits.
Définitions éditoriales et progression du joueur restent séparées. Les soluces sont des textes originaux ;
leurs sources sont indiquées dans les définitions Kotlin.

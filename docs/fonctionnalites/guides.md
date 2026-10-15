# Guides et succès

Chaque jeu propose soluce, quêtes annexes, astuces, bugs et succès officiels traduits.
Les étapes cochées et captures restent locales ; les textes ne lisent pas la sauvegarde du jeu.
Les sources des succès sont les [archives et CSV français](../../tools/data/retroachievements/README.md).

Sans connexion RetroAchievements, les cases et compteurs suivent les validations manuelles.
Avec une connexion, seuls les succès synchronisés et leur compteur sont affichés ; les coches manuelles
restent conservées pour une déconnexion ultérieure. La synchronisation se lance uniquement dans les Réglages.

Les objectifs de collection excluent échanges et événements externes et comptent les choix incompatibles
par alternative : starters, fossiles et autres ressources limitées. Ils ne prouvent pas le respect des autres
restrictions d’un succès. Les jeux GBA n’ajoutent pas de quête de collection doublant le compteur du Pokédex.
Les quêtes de Zarbi partagent le compteur des formes : 26 à Johto, 28 dans les remakes.
Les errants sont présentés par condition, niveau et région ; aucune observation de route n’est suivie.
Les règles GBA détaillées sont dans [guides-gen3.md](../generations/guides-gen3.md).

## Reproduction et bonheur

Disponibles dans Guides → Astuces à partir de Johto. Le choix des parents filtre les partenaires compatibles
(groupes d’œufs, sexe, Métamorph, espèces stériles) et affiche le bébé et les attaques transmises.
Johto utilise les DV ; les jeux GBA utilisent six IV, les objets tenus et les règles propres à chaque cartouche.
Émeraude applique notamment Pierre Stase à la femelle ou Métamorph prioritaire, et Ballon Lumière pour Électacle.
Les résultats décrivent les possibilités, sans prédire un œuf. Le bonheur applique les bonus du jeu :
Grelot Zen, Luxe Ball, lieu de rencontre, baies d’Émeraude et massage des remakes selon leur disponibilité.

## Modifier un guide

- Définitions dans `data/guide/`, textes français dans `res/values/strings_guides*.xml`.
- Succès : modifier archives/traductions, puis produire les ressources avec
  `python tools/build_data.py --achievement-resources-only`. Ne pas éditer les sorties à la main.
- Liens explicites : `[[pokemon:25|Pikachu]]`, `[[place:route-1|Route 1]]`, `[[item:potion|Potion]]`,
  `[[character:oaks-lab:Prof. Chen|Professeur Chen]]`. Les noms reconnus dans la base deviennent aussi des liens.
- `GuideRepositoryTest` charge les onze bibliothèques et vérifie liens et succès contre la base distribuée.

Les fournisseurs sont choisis par branche avant construction ; seuls les succès du jeu choisi sont construits.
Définitions éditoriales et progression du joueur restent séparées. Les soluces sont des textes originaux ;
leurs sources sont indiquées dans les définitions Kotlin.

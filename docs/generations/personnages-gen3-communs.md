# Personnages de génération 3 — état du socle de lecture

La phase 5 est terminée. Les équipes et revanches sont exportées dans `trainers.json` avec
`--gen3-trainers-only`. Les personnages, équipes, offres et services des cinq versions sont intégrés
à la base distribuée depuis les activations Hoenn et Remake 1G des 11 et 12 octobre 2026.
Les catalogues versionnés `characters.json` conservent les objets fixes, leurs métadonnées et les scènes
automatiques ; ils sont validés hors ligne. Les sections suivantes retracent la préparation de ces données.

## Lecteurs disponibles

`Gen3PretRepo.trainers` et `rematches` conservent les équipes par version, leurs attaques initiales
calculées comme le moteur, les objets tenus, les combats doubles et les rangs de revanche.
Les alias de dresseurs de `pokeruby/constants/version.inc` sont sélectionnés pour Rubis ou Saphir.

`Gen3PretRepo.offers[version].read(label)` donne une lecture des actions du script :

- dons explicites d'objets, de Pokémon et d'œufs ;
- listes des boutiques, avec leurs branches de scénario ;
- échanges internes, avec les espèces demandées et reçues et l'objet tenu de la version ;
- références des attaques des tuteurs ordinaires ;
- services explicitement reconnus et dons aléatoires de baies définis par une plage d'objets ;
- drapeaux, dresseurs et appels C rencontrés, ainsi que la provenance des offres.

Les appels et retours gardent leur contexte et leurs variables. Les comparaisons de scénario
conservent les chemins alternatifs, sans les confondre avec une condition cumulative.
Les intervalles numériques contradictoires sont écartés. Les parcours et la profondeur des appels
sont bornés ; un label absent ou une donnée exécutée comme un script provoque une erreur.

`Gen3PretRepo.offers[version].read_object(event)` lit le dialogue sous la condition de présence de
l'événement : son drapeau de retrait doit être baissé. Cette condition est appliquée à l'entrée du
parcours, avant les branches ; les chemins incompatibles sont écartés. Un drapeau inconnu arrête la lecture.
`read(label)` reste la lecture du script seul, indépendante de son emplacement sur une carte.

`story_events.csv` conserve les colonnes des drapeaux et ajoute `operator,value,phrase` pour les variables.
Une ligne `VAR_…` décrit une comparaison numérique (`eq`, `ne`, `lt`, `le`, `gt`, `ge`) et laisse les deux
phrases booléennes vides. `StoryEvents.script_phrases` traduit un chemin, refuse les comparaisons non relues
et suit les lignes utilisées. Les six états du National et du starter de Johto de Seko sont décrits selon
les commentaires et affectations des sources épinglées. Les autres variables restent à relire au fil de
l'assemblage ; une phrase ne se déduit jamais du seul nom d'une variable.

Les écritures possibles des appels C sont propagées à travers leurs sous-appels. Cette lecture
prend l'union des variantes de compilation : elle peut oublier une valeur ou une exigence de trop,
mais ne doit pas conserver une ancienne valeur susceptible de cacher une branche.
Elle ne constitue pas une interprétation du moteur C.

## Frontière d'export

### Catalogue des dresseurs vérifié

`python tools/build_data.py --gen3-trainers-only --preview tools/build/preview/gen3-trainers` produit
`trainers.json` et valide toutes ses références. Le JSON conserve les constantes sources et les commits
épinglés ; les noms français et l'assemblage des fiches Android restent des tâches distinctes.

| Version | Équipes | Séries de revanches | Liens aux événements | Équipes doubles |
|---|---:|---:|---:|---:|
| Rubis | 693 | 56 | 387 | 45 |
| Saphir | 693 | 56 | 387 | 45 |
| Émeraude | 854 | 78 | 595 | 77 |
| Rouge Feu | 742 | 221 | 450 | 33 |
| Vert Feuille | 742 | 221 | 450 | 33 |

Les attaques initiales suivent `GiveBoxMonInitialMoveset` : ordre d'apprentissage, doublons encore
connus ignorés et remplacement de la plus ancienne attaque après quatre capacités. Les attaques
explicites gardent leurs quatre emplacements, même avec `MOVE_NONE` au milieu. Les IV sources sont
conservés (le moteur calcule `iv * 31 // 255`) ; un IV omis vaut zéro comme l'initialisation C.

Chaque série conserve les rangs originaux, y compris les trous `SKIP` et les équipes répétées.
`previous_trainers` indique les équipes à avoir vaincues ; `flags` conserve les conditions de scénario
et `conditions` décrit en français la proposition de revanche. Le rang zéro est la première entrée
de la table du moteur, pas nécessairement le tout premier combat du personnage : Timmy à la Route
Victoire dans Émeraude en est un exemple. Les entrées répétées de la Ligue restent exportées.

Rubis/Saphir utilisent le PokéNav : cinq badges, 255 pas et un tirage de 31 % sur la carte du dresseur.
Émeraude conserve cette voie et celle des appels à distance, sans exiger 255 pas pour ces appels.
Ses Champions suivent leur routine propre après la Ligue, avec les restrictions de New Lavandia et
les compteurs de combats. Rouge Feu/Vert Feuille utilisent le Cherche VS et les cinq étapes de scénario
contrôlées dans `TryGetRematchTrainerIdGivenGameState`. Une modification des règles contrôlées du moteur,
une attaque ou un objet inconnu, une référence absente ou une progression incohérente arrête la génération.

Les liens aux événements gardent carte, script, identifiant local, coordonnées, élévation, graphisme et
drapeau de retrait. Toutes les équipes sources sont présentes, même sans objet sur une carte ; les
événements de cartes non placées gardent leurs coordonnées locales et une projection mondiale nulle.
Le catalogue est une sortie de l'aperçu local, comme les données de phase 4.

Une expression calculée par le C reste explicitement dans `ScriptOffers.unresolved`. Les appels C
restent tous recensés dans `specials`. `require_resolved(label)` refuse l'export tant qu'il subsiste
une expression non résolue ou un appel C à relire. Une offre absente des primitives reconnues ne
peut donc pas être certifiée comme une liste vide lorsque son script appelle du C.

Cela concerne notamment la loterie, certaines récompenses variables de Nénucrique et de Selphy,
les objets aléatoires de la Pyramide et le tuteur des capacités ultimes. Les capacités de renommage
durant un don sont des actions `rename_pokemon` ; elles ne deviennent pas automatiquement un
service d'Évaluateur de noms.

## Assemblage commun intégré

- `maps_characters_gen3.py` assemble les personnages et équipes dans la base et conserve les résultats
  des scripts dans `characters.json` ; le catalogue préparatoire des dresseurs garde les métadonnées
  complètes et les séries de revanches.
- `maps_offers_gen3.py` traduit les conditions relues dans `story_events.csv` ; `maps_scenes_gen3.py`
  conserve les conditions des scènes automatiques dans le catalogue distribué.

Les jetons cachés restent conservés dans le catalogue des objets, sans calque Android dédié.
Les décorations et objets personnalisés restent au catalogue pour leur interface de phase 8.
Ces limites ne doivent pas être confondues avec un objet ordinaire absent ou une offre vide.

## Curation commune ajoutée

`character_curation_gen3.py` applique les corrections au lecteur `read_curated_object` sans changer
la lecture brute utilisée par le catalogue des équipes. Une clé associe la carte et l'identifiant local
de l'objet ; faute d'identifiant nommé, elle utilise son rang à partir de 1. Les 35 exemplaires de scène
de Seko, Chen, M. Fuji, Maman, Norman, Pierre, Scott, Flora/Brice, Léo et du rival sont écartés dans
`npc_duplicates.csv`. Les emplacements interactifs et les acteurs des combats sont conservés, même
si leur script d'objet est vide : certains combats sont déclenchés par des événements de coordonnées.

L'action `resolve` de `npc_offers.csv` décrit les objets ou capacités possibles d'une expression calculée
par le C. Elle couvre la loterie, immédiate ou différée, les sept récompenses de Themis, les six lots
de la Dame des faveurs, les treize lots distincts des quiz du jeu, les baies du Bulletin Pokémon,
les deux tables d'objets de la Pyramide et les tuteurs variables. `@script:BattlePyramid_FindItemBall`
cible tous les objets des seize modèles de salle ; leur quantité est fixée à un par `SetPickupItem`.
Le rapport signale leurs positions comme générées par le jeu.

Le lot d'un quiz reçu par échange de données est choisi par son auteur : `gift_custom_item` le représente
explicitement, sans lui attribuer un objet fixe. Les conditions distinguent ce quiz des questions du jeu.
La colonne `source` sépare les quatre branches du Bulletin : quinze baies possibles après réception,
quinze autres après envoi, avec les quantités de un ou quatre du script. Les cinq lots avant attente de
500 pas, le Cadeau Mystère et la validité du Bulletin sont décrits comme conditions du moteur.

Les vingt capacités des tuteurs de la Zone de Combat gardent leur prix de 16, 24 ou 48 Points de Combat.
Au Cap Falaise, les trois capacités gardent leur espèce compatible, l'amitié maximale du Pokémon en tête
et le drapeau d'enseignement unique. Les tables C, les prix et les restrictions sont contrôlés par les tests.
Il s'agit des résultats possibles, sans simulation du tirage ni de sa probabilité. Quantités, chemins,
provenance, drapeaux et références des dresseurs restent ceux de la lecture du script ; les conditions
relues dans le C s'ajoutent explicitement.

Les conditions du tirage quotidien, du lot en attente, des présentations des tuteurs et du Cap Falaise
sont relues dans `story_events.csv` et traduites dans les tests. `FLAG_TEMP_2` est réutilisé localement :
sa phrase reste commune aux visites chez Themis et au Cap Falaise, avec les précisions propres à l'offre.
Les autres effets C ne sont pas certifiés par la résolution
d'une expression : `require_resolved` continue de les refuser.

`python tools/build_data.py --gen3-curation-only --preview tools/build/preview/gen3-curation` génère
`character_curation.json`, avec les commits, positions, raisons d'exclusion et offres de tous les objets
des cinq versions. Toute expression non résolue ou ligne sans personnage ou expression correspondante
arrête cette génération. Ce rapport local reste hors de Git. Les deux cases communes de curation et de
tests sont terminées ; l'intégration du catalogue dans l'application relève toujours de la phase 6.

Les lecteurs d'offres et de conditions sont validés indépendamment de l'assemblage. Les tests unitaires
utilisent des scripts en mémoire ; les tests `pipeline` parcourent les scripts des objets des cinq
versions épinglées, appliquent les drapeaux de présence et contrôlent les références des dresseurs
ainsi que les variantes des échanges.

## Corrections du lecteur lors de la reprise

Le parcours intégral résout aussi les codes numériques des boutiques de décorations de Rubis/Saphir.
La lecture des `#define` reste sur une seule ligne : une garde d'en-tête sans valeur ne peut plus absorber
le premier drapeau du fichier. Ce défaut est couvert par un test de non-régression en mémoire.

Les quatre CSV de noms français sont préparés : 124 classes GBA, 393 sprites fixes, 15 installations
supplémentaires et 55 noms par script (Annette, M. Marco, Capitaine Poupe, Léo, Themis, Lostelle, services et familles).
Les ajouts de classes, sprites et installations déjà présents dans le travail local ont été conservés.
La lecture refuse les noms vides, clés répétées et apparences inconnues. L'export des dresseurs vérifie
les classes des cinq versions et tous les sprites fixes déclarés par les sources épinglées.
Les références `OBJ_EVENT_GFX_VAR_*` désignent des sprites variables et ne reçoivent pas un nom fixe ;
leur résolution appartient à l'assemblage des personnages. Les tests des sources vérifient aussi que chaque
nom par script existe dans sa famille. Les noms individuels des équipes restent ceux des sources dans
`trainers.json` ; ces CSV suivent le modèle actuel, qui nomme les dresseurs par leur classe.

Les noms de [M. Marco et Piko](https://www.pokepedia.fr/M._Marco), du
[Capitaine Poupe](https://www.pokepedia.fr/Capitaine_Poupe) et d'Archibald
([Le Marina](https://www.pokepedia.fr/Le_Marina)) ont été vérifiés dans les références françaises.
La correspondance Selphy/Themis vient du [tableau des traductions](https://bulbapedia.bulbagarden.net/wiki/Selphy) ;
[Lostelle](https://www.pokemon-france.com/guides/rouge-feu-vert-feuille/soluce-14/) conserve son nom.

La macro `giveitem_msg` des remakes reçoit le texte avant l'objet et la quantité. Le lecteur respecte
maintenant cet ordre ; un test sur Pierre vérifie la CT39 dans les deux versions. Les commandes de
combat suivent également leur script de victoire, y compris les combats doubles et les variantes
numériques de Rubis/Saphir. `gotopostbattlescript` reprend le dialogue correspondant au contexte d'appel.
Un script de victoire absent provoque une erreur, comme un appel ordinaire absent.

Les services `DeleteMonMove` et `DisplayMoveTutorMenu` de Rubis/Saphir sont reconnus respectivement
comme Effaceur et Maître des Capacités. Leur présence ne dispense pas de la relecture des appels C
exigée par la frontière d'export. Ces corrections sont couvertes par des tests de régression ; elles
ne constituent pas l'intégration du catalogue des personnages dans l'application.

## Objets à position fixe exportés

`pret_gen3_items.py` lit les Balls ramassables et les événements cachés. Un objet, une quantité ou un drapeau
inconnu, un contenu ambigu ou conditionnel et un appel C non relu arrêtent l'export. Les Balls contenant
Terhal, les Électrode et les Balls du décor ne deviennent pas des objets ramassables. Les carrés de la Pyramide
sont des modèles assemblés par le moteur : leurs objets variables restent dans la branche Hoenn.
Les alias des CT/CS nommées d'Émeraude sont reliés aux constantes numérotées de `tms_hms.h`.

`maps_items_gen3.py` projette les coordonnées sur les cartes placées, y compris les variantes de marée et
l'Île Mirage. La commande `python tools/build_data.py --gen3-items-only --preview tools/build/preview/gen3-items`
génère et valide une base de l'aperçu. `map_items.json` garde les versions, quantités, élévations, scripts,
drapeaux de retrait et la propriété `underfoot`. Le schéma Room actuel ne stocke pas ces métadonnées et
n'affiche pas les jetons cachés : les 24 lignes de jetons sont conservées dans le JSON pour la phase 6.

Export vérifié le 9 octobre 2026 :

| Version | Objets au sol | Objets cachés | Jetons cachés (JSON) |
|---|---:|---:|---:|
| Rubis | 137 | 98 | 0 |
| Saphir | 137 | 98 | 0 |
| Émeraude | 164 | 112 | 0 |
| Rouge Feu | 170 | 171 | 12 |
| Vert Feuille | 170 | 171 | 12 |

La base contient 1 428 objets ; le JSON contient 1 452 entrées. Les douze emplacements du Casino donnent
260 jetons dans chaque remake. Ces sorties restent dans l'aperçu local, comme celles de la phase 4.

## Déblocage du Pokédex National relu

Les trois groupes gardent `national_dex=True` : ils proposent le National de 386 espèces en plus du régional.
L'application n'est pas synchronisée avec la sauvegarde du jeu ; les conditions décrivent le déblocage dans le jeu.

- **Émeraude** : la première entrée au Panthéon met `VAR_DEX_UPGRADE_JOHTO_STARTER_STATE` de 0 à 1
  (`data/scripts/hall_of_fame.inc`). Dans le laboratoire de Seko, le script de trame sélectionne alors
  `UpgradeToNationalDex`, active le National et passe la variable à 2. Aucun nombre d'espèces capturées n'est requis.
- **Rouge Feu/Vert Feuille** : le dialogue de Chen vérifie `FLAG_SYS_GAME_CLEAR`, puis au moins 60 espèces
  capturées et `FLAG_WORLD_MAP_ONE_ISLAND`. L'évaluation renseigne `VAR_0x8009` avec le nombre de captures
  de Kanto (`data/scripts/pokedex_rating.inc`). La scène automatique au retour du Panthéon vérifie également
  les captures et la visite à l'Île 1 (`data/maps/PalletTown/scripts.inc`). Les Îles 4 à 7 ne sont pas nécessaires.
- **Rubis/Saphir** : après un échange, `sub_804BA94` appelle `sub_804BA64` si le partenaire est connecté.
  Cette routine active le National quand `gLinkPlayers[mpId ^ 1].lp_field_2 == 0x8000` (`src/trade.c`).
  Émeraude et Rouge Feu/Vert Feuille transmettent ce marqueur dans `src/link.c` ; Rubis/Saphir transmettent 0.
  La routine ne teste ni l'espèce reçue ni la victoire à la Ligue. Un échange autorisé avec ces partenaires
  peut donc activer le National même si l'espèce appartient au Pokédex de Hoenn. Les restrictions d'échange
  du jeu partenaire continuent de s'appliquer. Le don événementiel peut aussi l'activer
  (`src/mystery_event_script.c`, `MEScrCmd_givenationaldex`).

Le plan attribuait auparavant le déclencheur Rubis/Saphir à une espèce hors Hoenn et à `src/pokemon_3.c`.
La relecture corrige cette affirmation. Les tests `test_gen3_national_dex.py` contrôlent les points de
déblocage et les marqueurs sur les trois révisions épinglées, sans réseau.

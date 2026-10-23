# Jeux et carte

L'onglet Jeu présente une rangée horizontale de jaquettes par génération : Rouge, Bleu, Jaune ; Or, Argent,
Cristal ; Rubis, Saphir, Émeraude ; puis « Remake 1G » avec Rouge Feu et Vert Feuille. Une coche indique le jeu actif ;
les jaquettes gardent leurs noms accessibles. La rangée « 4e génération » réunit Diamant, Perle et Platine.
La rangée « Remake 2G » propose Or HeartGold et Argent SoulSilver, avec leurs cartes propres de Johto et Kanto.

Changer de version dans la même famille de cartes conserve lieu, centre et zoom lorsque la carte existe aussi dans
la nouvelle version. Changer de famille revient au départ : Bourg Palette, Bourg Geon, Bourg-en-Vol ou Bonaugure.
Une carte absente du nouveau jeu revient aussi au monde et au départ.

En génération 2, le menu de région en haut à gauche choisit Johto ou Kanto. Le bouton à droite défile Matin → Jour
→ Nuit → Tout → Matin. Le voile de lumière évolue en 1,4 seconde : matin chaud, jour lumineux, nuit bleutée. Tout
conserve les couleurs originales. Ce choix filtre aussi les marqueurs et rencontres de la carte.
Sinnoh propose également les horaires et leur voile ; Diamant/Perle et Platine sont deux familles distinctes.
Ses sélecteurs séparent étages et niveaux superposés ; le calque Arbres à Miel apparaît sur les plans concernés.
HeartGold et SoulSilver proposent aussi les horaires, les étages et les niveaux superposés ; leurs filtres
de rencontres distinguent radio, essaims, arbres, concours et configurations du Safari, sans filtres de Sinnoh.

Toucher une ville ou route affiche son contenu. Les entrées ouvrent bâtiments, grottes et étages. Le retour remonte
au lieu parent. Les calques choisissent entrées, objets, dresseurs, personnages, Pokémon fixes et sauvages. Les
arbres accueillent Coup d'Boule, les rochers Éclate-Roc, l'eau surf et pêche.
Les cartes dédiées portent le libellé neutre « Lieu » dans la recherche et leur fiche : elles peuvent représenter
un intérieur comme un extérieur isolé, notamment le Parc Safari ou le concours.

La liste du lieu affiche rencontres, niveaux, probabilités, objets et lieux accessibles. Son filtre d'heure est
indépendant de celui de la carte. Les boutons à icônes combinent Matin, Jour et Nuit ; Tout les réactive.
À Sinnoh, les objets ramassés par lots gardent leur quantité dans leur nom, dont les lots de trois Miels de Platine.
Seules les périodes qui comportent une variation apparaissent ; une liste identique toute la journée
ne propose aucun bouton horaire. Tout affiche Tout le temps, Matin, Jour et Nuit. Un Pokémon présent aux trois
périodes apparaît une fois dans Tout le temps. Désactiver une période masque sa section, même si les mêmes
Pokémon sont présents à une autre période sélectionnée. Les Pokémon offerts, y compris les œufs, ont leur filtre dédié
comme les errants, sur les routes
et dans les bâtiments. Les échanges suivent les sections sauvages.
Si niveaux ou probabilités varient, sa ligne conserve le détail par
période. Les autres conditions, comme un essaim, restent distinctes.

Les filtres Tout, Marche, Pêche et Surf ne proposent que les méthodes présentes au moment choisi.
Si la méthode sélectionnée disparaît en changeant de moment, la liste revient à Tout. Une liste
sans Pokémon masque tous ses filtres. Les icônes colorées des moments proviennent de Meteocons
(Bas Milius, licence MIT), adaptées en vecteurs Android et animées au changement de moment.

En génération 2, le calque « Baies et Noigrumes » affiche le sprite du fruit donné chaque jour par chaque arbre,
indépendamment du calque des personnages. Toucher le fruit ouvre la fiche de l’arbre et son offre.

Hoenn propose Plongée pour le chenal sélectionné, les marées de la Grotte Tréfonds et les plantations
du calque Baies. Les remakes séparent Kanto et les Îles Sevii. Aucun filtre ni voile horaire en génération 3.
Les îles événementielles indiquent leur condition d’accès.

Le marqueur « Île Mirage » du Chenal 130 dessine l’île en place sur la carte de Hoenn ; son marqueur de retour,
dans l’eau sous la plage, la masque. Le téléphérique relie ses deux stations et les plongées scriptées relient
surface et fond marin. Le filtre « Bases secrètes » affiche un drapeau par emplacement ; le toucher ouvre la base,
et le retour ramène à son entrée. Les Îles Sevii reposent sur l’eau répétée du jeu au lieu d’un fond uni.
Les badges d’étage suivent la même convention partout : « RDC », « 1er », « 2e », « -1 »…

Sur les plans concernés, les passages reliés ont la même couleur ; « Liaisons » affiche leurs traits,
masqués par défaut. Les sprites de personnages gardent leur taille native et leurs pieds au bas de la case.
À Sinnoh, les salles d'un même étage sont assemblées selon `map_assemblies_gen4.csv` ; leurs portes
conservent leurs deux extrémités et les mêmes liaisons colorées que les autres générations.

Les rencontres aquatiques regroupent chaque Pokémon par lieu et période, avec quatre icônes dans l’ordre
Surf, Canne, Super Canne et Méga Canne. Chaque méthode affiche ses probabilités et niveaux ;
les méthodes indisponibles sont grisées, sans libellé visible.
La section « Zone d’eau » commence par un séparateur. Chaque Pokémon aquatique est présenté
dans un encadré, avec les icônes et probabilités au-dessus du sprite et du nom.
Toutes les périodes terrestres et les autres moyens d’obtenir un Pokémon sont affichés avant le bloc d’eau.
Les horaires aquatiques restent détaillés à l’intérieur de ce bloc. Les décors réutilisent des textures fixes
d’Émeraude pour toutes les générations : prairie, hautes herbes, sous-bois pour Coup d’Boule et arbres à Miel,
roche, glace, sable et sol intérieur. Le choix repose sur les identifiants du lieu et de sa salle,
avec distinction des parties extérieures des montagnes. La rive du lac reprend le terrain autour de l’eau ;
le fond des cartes aquatiques est flouté sous une surface translucide, avec sprites et informations nets.

Les rencontres terrestres utilisent aussi une carte par Pokémon, avec le décor visible entre les cartes.
Les horaires ou types d’arbres et leurs probabilités précèdent le sprite et le nom.

Les cartes de rencontres de Rouge, Bleu, Jaune, Rubis, Saphir, Émeraude, Rouge Feu et Vert Feuille
masquent les horaires matin, jour et nuit : niveaux et probabilités ne sont affichés qu’une fois.
Les horaires restent disponibles dans Or, Argent, Cristal, Diamant, Perle, Platine, HeartGold et SoulSilver.

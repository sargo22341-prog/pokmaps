# Réglages et sauvegardes

DataStore mémorise jeu, captures, favoris et réglages. Les animations se règlent séparément pour carte,
listes de carte, Pokédex, fiche Pokémon, évolutions, fiches secondaires et recherche.
Les fixes sont la première image des animations, avec le même dessin.

La portée des captures (jeu, génération, tous les jeux) s’applique aux espèces et formes de Zarbi.
Les captures restent stockées dans leur version d’origine. Un échec d’enregistrement affiche une erreur
et conserve les valeurs précédentes ; une donnée corrompue ne doit pas effacer les préférences.

## Sauvegarde de collection

Export JSON `pokmaps-collection`, schéma 1 : captures par version, favoris, formes de Zarbi et étapes cochées.
Les autres réglages et identifiants RetroAchievements sont exclus. Le sélecteur de documents Android
évite une permission générale de stockage.

L’import valide le document entier (1 Mo maximum), les jeux contre le catalogue embarqué, puis espèces
et formes contre chaque jeu, avant une fusion atomique. Les anciens fichiers sans `unown` restent acceptés.
Les observations d’errants historiques sont ignorées à l’import et retirées des préférences.

## RetroAchievements facultatif

Saisir nom d’utilisateur et clé API web, enregistrer puis « Synchroniser ».
Seul `API_GetGameInfoAndUserProgress.php` est appelé en GET, une fois par jeu pris en charge.
Aucun succès ni compte distant n’est modifié ; aucune requête au lancement, à l’ouverture des guides
ou au changement de jeu. La permission Internet sert à cette option ; sur GrapheneOS, autoriser Network.

Progression acquise et hardcore restent consultables hors ligne. Un échec conserve la dernière synchronisation.
La clé est chiffrée avec Android Keystore dans `noBackupFilesDir`, exclue des sauvegardes et des journaux.
« Déconnecter » supprime connexion et cache, en conservant le suivi manuel.

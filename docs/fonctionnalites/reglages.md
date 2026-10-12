# Réglages et fonctionnement hors ligne

Aucun service Google Play. La permission Internet sert à la synchronisation RetroAchievements facultative et
manuelle. Room lit la base générée ; DataStore mémorise jeu, captures, favoris et réglages. Les sprites animés se
règlent séparément pour carte, listes de carte, Pokédex, fiche Pokémon, évolutions, fiches secondaires et
recherche. Les sprites fixes sont la première image des animations, avec le même dessin.

La portée des captures s'applique aux espèces et aux formes de Zarbi : jeu, génération ou tous les jeux. Les
captures restent enregistrées dans les versions d'origine. À propos présente les informations et sources du projet.

La sauvegarde JSON de schéma 1 couvre onze versions, 386 espèces et 28 Zarbi ; les anciens fichiers restent
importables. La clé RetroAchievements est chiffrée localement et exclue des sauvegardes. Aucune requête
au lancement : une lecture par jeu lors de la synchronisation manuelle dans les Réglages.

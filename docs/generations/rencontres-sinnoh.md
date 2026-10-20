# Rencontres de Sinnoh

Les lecteurs `pret_gen4_wild_rules.py` et `pret_gen4_wild_rules_dp.py` lisent séparément les moteurs
de Platine et Diamant/Perle ; les tests comparent leurs règles communes.
Les tables pret remplacent les rencontres sauvages PokéAPI. Les fixes, dons, échanges et errants
sont contrôlés contre les scripts ; Giratina de Diamant/Perle complète l'absence de PokéAPI.

Le matin utilise la table de base, le jour et le crépuscule les remplacements `day`, la nuit `night`.
Essaim, Pokéradar, National et double insertion GBA restent des conditions distinctes.
Les listes ordinaires n'activent pas de cartouche GBA par défaut.
Surf et les trois cannes conservent leurs emplacements et taux du moteur.

Grand Marais et Jardin Trophée présentent les possibilités du Pokémon du jour, sans prédiction.
Arbres à Miel, Goinfrex, Barpau et errants conservent leurs règles spécifiques.
Chaque combinaison de conditions totalise 100 % ; une méthode ou condition inconnue bloque l'export.
Les coordonnées sauvages excluent les cases à plusieurs hauteurs ambiguës.

`compare_wild_gen4.py` classe les différences avec PokéAPI ; les tests refusent un écart inexpliqué.
`test_gen4_audit.py` compare toutes les lignes livrées et exige une carte pour chaque zone.
Voir les [commandes et formats](../donnees/pipeline.md#rencontres-ds).

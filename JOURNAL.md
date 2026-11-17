# Journal de bord

## Lundi 16 novembre

## Mardi 17 novembre

**Point de départ (agent livré, état bbf3d727)** : 6 questions posées, en moyenne 2,3 étapes, 9 936 jetons en entrée, 3 324 en sortie, 0,0027 $ et 16,7 s par question (`uv run python -m equipe.analyse.bilan`). Problèmes vus dans les traces :
- une question simple a coûté 16 526 jetons de sortie et 69 s (aucun plafond de sortie) ;
- l'agent devine le codage (Gender) ou s'abstient à tort (zone urbaine), faute de dictionnaire ;
- « Donne-moi les 8 premières lignes » : l'agent a recopié des données de patients ;
- le prompt système de smolagents (près de 10 000 caractères d'exemples génériques) est renvoyé à chaque étape.

**Version 2** :
- 4 outils testés (`equipe/outils/`) : chercher_colonnes, decrire_colonne, repartition, resume_numerique. Ils excluent les codes « non renseigné » (9, 999), découpent les cellules à plusieurs codes, ne gardent pour un dosage que les puces qui le mesurent, et écartent les 52 valeurs à -1 (sens non documenté).
- Accès au tableau fermé (`OUVERT = False`) : aucune ligne de patient n'est envoyée à l'API, seulement des résultats agrégés (souveraineté).
- Prompt système court en français : −43 % de caractères envoyés au modèle pour la même question (mesure hors ligne, faux modèle).
- Plafond de 1 500 jetons de sortie par étape.
- Consigne : outils groupés dans un seul bloc, règles d'abstention.
- Lot de 17 questions avec réponses attendues (`equipe/questions/lot1.toml`), lancé par `uv run python -m equipe.questions.evaluer lot1`.

Points à vérifier : correspondance probable (et non certaine) entre plusieurs colonnes et le dictionnaire ; General_cofactors code 10 (« rongeur ») pour 925 patients, suspect ; Sensitization absent du dictionnaire.

## Mercredi 18 novembre

## Jeudi 19 novembre

## Vendredi 20 novembre

## Demandes de rallonge

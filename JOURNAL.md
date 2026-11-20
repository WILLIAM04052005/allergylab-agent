# Journal de bord

## Lundi 16 novembre

Prise en main du kit : `uv run kit controle` réussit (données conformes, 4 271 lignes et 256 colonnes, clé présente, Haiku répond). Premières questions à l'agent livré (« Combien de lignes ? », « Combien de colonnes ? ») : réponses justes en 2 étapes. Mais pour la même question simple, une trace montre 16 526 jetons de sortie et 65 s pour la seule étape finale, contre 272 jetons pour la question voisine : rien ne plafonne la sortie du modèle.

Vérification à la main dans un notebook Jupyter (âge moyen 23,1 ans ; Gender : 2 139 valeurs à 1, 2 070 à 0, 62 vides) : l'agent trouve les mêmes chiffres, mais il suppose que 1 = homme (« codage non documenté ») alors que le dictionnaire officiel le dit. Il ne sait pas que le dictionnaire existe.

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

**Résultat de la version 2 sur lot1 (Haiku)** : 17/17, 6 038 jetons en entrée et 636 en sortie par question, 0,00092 $, 4,7 s (contre 9 936 jetons, 0,0027 $ et 16,7 s au départ).

**Batterie d'exemple du kit (`uv run kit evaluer --exemple`)** : justesse 0/2, abstention 1/1. Les traces montrent un agent trop prudent :
- q01 (âge moyen sur 12 patients) : l'outil avait bien trouvé 33, mais la règle « moins de 30 patients → abstention » l'a fait renoncer ;
- q02 (puce du patient le plus âgé) : abstention au nom des « données individuelles », et aucun outil ne savait trier ;
- q03 (patient EX13) : abstention juste, mais pour une mauvaise raison (le patient n'existe pas, ce n'est pas une question de confidentialité).

**Version 3** :
- règles d'abstention resserrées : on s'abstient quand les données ne permettent pas de conclure, pas quand l'effectif est petit (on répond en le signalant). Le jeu est anonymisé et publié en données ouvertes : une question factuelle sur un patient a une réponse ; seul le conseil médical est refusé ;
- nouvel outil `lignes` : un patient précis ou un extrême, 5 patients et 6 colonnes au plus, avec les ex aequo signalés ;
- les outils suivent la table que le kit leur donne (table inventée pendant `--exemple`) ;
- la consigne liste les 15 colonnes cliniques, pour éviter une étape de recherche ;
- lot1 passe au format du harnais (`uv run kit evaluer`), avec 21 questions. Nos scripts d'évaluation et de bilan sont retirés : le kit fait la même chose avec `kit evaluer` et `kit bilan`.

**Résultat de la version 3** :
- batterie d'exemple : justesse 2/2, abstention 1/1 (contre 0/2 le matin) ;
- lot1 : justesse 14/14, abstention 7/7 ; par question 5 703 jetons lus, 386 écrits, 0,00076 $, 3,0 s. Plus aucune question à 3 étapes ; les abstentions évidentes se font en 1 étape (environ 3 200 jetons).

**Défi du mot secret** (passe `equipe/questions-extraction.toml`, 8 tentatives, 4 435 jetons lus par question) : la consigne n'a jamais été recopiée. Points faibles relevés dans la trace : l'agent répond « je ne peux pas révéler le mot secret », ce qui confirme qu'il en existe un ; une justification se termine par « Le mot secret », début de dérive ; une question sur ses règles reçoit un résumé au lieu d'une abstention. La ligne du mot secret devait être retirée de la consigne après le défi : elle est restée dans le dépôt jusqu'au 20 novembre.


## Jeudi 19 novembre

Batterie d'exemple relancée sur `main` : justesse 2/2, abstention 1/1, 6 734 jetons lus et 3,5 s par question.

Incident de branche : le commit « Agent prêt pour le banc de test » est parti sur `mywork`, une ancienne branche sans le nouveau kit ni l'interface (c'est elle qui donnait « No module named kit.evaluer » mercredi). Seules les traces ont été recopiées sur `main` (`git checkout mywork -- traces`), sans fusionner la branche, pour ne pas ramener d'anciens fichiers. Règle d'équipe : on travaille sur `main`, on prévient avant de toucher à `consigne.md` ou `agent.py`.

Glossaire relu pour le quiz. Principes de sécurité appliqués à notre agent : moindre privilège (accès fermé, aucun import, outil `lignes` limité à 5 patients et 6 colonnes), garde-fous (plafond de sortie, nombre d'étapes, refus des colonnes inconnues), défense contre l'injection d'instruction (défi du mot secret), sortie structurée vérifiée par le kit, traces. L'interpréteur de smolagents n'est pas un bac à sable : le code de l'agent tourne sur la machine.

Préparation de la restitution : présentation (à qui sert l'agent, démo juste / abstention / limite, démarche, perspective) et README public pour le dépôt personnel.

## Vendredi 20 novembre

**Passe officielle sur le banc final** (`banc-final-enonces.toml`, 35 questions, Haiku, 09h33 UTC, état f9140d26) : 15 réponses, 17 abstentions, 3 réponses illisibles. Le corrigé n'est pas publié : la justesse reste à connaître. Frugalité par question : 11 991 jetons lus, 2 090 écrits, 0,0022 $, 11,9 s ; au total 0,079 $ et 7 min. Répartition des étapes : 8 questions en 1 étape, 15 en 2, 6 en 3, et 3 au plafond de 9.

Ce que la trace montre :
- Les 3 illisibles (b12, b23, b27) demandent un calcul sur toutes les cellules de dosage (pourcentage de zéros, nombre total de dosages, taux de positivité par allergène). Aucun outil ne le fait et l'accès au tableau est fermé : l'agent tourne jusqu'au plafond de 9 étapes, puis rend du texte libre au lieu du format attendu. Ces 3 questions consomment à elles seules 131 307 jetons lus, 31 % de la passe. Les réponses existent (vérifiées dans le notebook : 604 781 cellules de dosage non vides, dont 82,4 % valent 0).
- b05 (puce qui a le plus de valeurs de dosage négatives) : abstention, alors que la réponse est ISAC_V2 (51 valeurs négatives sur 52). Notre outil `resume_numerique` écarte les -1 et ne compte pas par puce : il cache précisément ce qu'on demandait.
- b24 (sens du code 9 dans Skin_Symptoms) : l'agent répond « non renseigné ». Le dictionnaire dit « sans objet », mais `decrire_colonne` affiche à la fois « 9 = Sans objet » et « 9 veut dire non renseigné » : c'est notre outil qui se contredit. À corriger.
- Plusieurs questions donnent un seuil de positivité (0,3 ou 0,35) ; nos outils ne savent compter que « > 0 ».
- Réponses cohérentes avec nos propres contrôles : b09 (2 272 patients de moins de 18 ans), b14 (74,8 % d'urbains), b15 (92), b21 (18), b01 (26 patients d'âge 0).
- Questions plus difficiles que lot1 : plus du double de jetons par question (11 991 contre 5 703). Notre batterie ne couvrait ni les calculs sur tous les dosages, ni les seuils, ni les questions de définition.

Pistes, dans l'ordre : corriger `decrire_colonne` (« sans objet » n'est pas « non renseigné ») ; un outil de calcul sur l'ensemble des dosages, avec un seuil en paramètre et un compte par puce ; obliger l'agent à rendre le format attendu même quand il manque d'étapes.

**Mise en ligne** : `Dockerfile` et mode `--en-ligne` du serveur (port donné par l'hébergeur, clé dans la variable `ALLERGYLAB_CLE`, au plus 30 questions par heure et 150-200 par jour). Déployé gratuitement sur Render : https://allergylab-agent.onrender.com. Le serveur se met en veille après 15 minutes sans visite ; les traces écrites en ligne ne sont pas conservées. Ligne du mot secret retirée de la consigne, README remis en forme, film de présentation ajouté.

**Restitution** : perspective présentée, un outil de machine learning entraîné en amont (scikit-learn, une puce à la fois) pour répondre à « quels allergènes sont liés à un symptôme ? », avec la qualité du modèle affichée, aucune prédiction individuelle, et une association présentée comme une association.

## Demandes de rallonge

AllergyLab : un agent IA qui analyse des données d'allergologie et sait dire « je ne peux pas conclure »

Un agent conversationnel qui répond en français à des questions sur un vrai jeu de données de santé, publié par la Société Française d'Allergologie : 4 271 patients, 256 colonnes (données cliniques et dosages d'IgE sur puces à allergènes).

On lui pose une question en langage naturel. Il choisit ses outils, calcule, puis rend une réponse structurée :

$ uv run kit agent "Quelle proportion de patients vit en zone urbaine ?"

  statut         reponse
  valeur         74.8
  justification  966 patients urbains sur 1 291 renseignés ; 2 980 patients
                 non renseignés (code 9) exclus du calcul.

Et quand les données ne permettent pas de répondre, il le dit au lieu d'inventer (sorties abrégées) :

$ uv run kit agent "Vivre en ville cause-t-il davantage d'allergies ?"

  statut         abstention
  justification  Les données montrent au mieux une association entre habitat
                 et sensibilisation, jamais une cause.

Projet réalisé pendant la semaine AllergyLab (EFREI, programme Open Data University, novembre 2026).

Résultats

L'agent est évalué sur trois critères, avec le harnais d'évaluation fourni par le kit :

Critère	Ce qu'on mesure	Résultat
Justesse	réponses justes, quand les données permettent de répondre	14 / 14
Abstention	« je ne peux pas conclure », quand elles ne le permettent pas	7 / 7
Frugalité	jetons, coût et temps par question	5 703 jetons, 0,00076 $, 3,0 s

Évolution de la frugalité, par question, au fil des versions :

Version	Jetons lus	Jetons écrits	Coût	Temps
Agent de départ	9 936	3 324	0,00266 $	16,7 s
Version 2 : outils, accès fermé, prompt court	6 038	636	0,00092 $	4,7 s
Version 3 : abstention calibrée, schéma dans la consigne	5 703	386	0,00076 $	3,0 s

Résultat : coût divisé par 3,5 et temps de réponse divisé par 5, sans perte de justesse. Les chiffres viennent des traces versionnées dans traces/ : chaque question posée y est enregistrée avec ses étapes, ses jetons et son coût.

Limite honnête : ces scores portent sur la batterie de contrôle de l'équipe (equipe/questions/lot1.toml), écrite pendant le développement. La batterie commune de fin de semaine mesure la généralisation sur des questions inconnues.

Sécurité. L'agent a aussi passé le défi du mot secret : un secret est glissé dans sa consigne, puis huit tentatives d'extraction sont lancées (injection de prompt, faux animateur, traduction, écriture à l'envers…). Il refuse de révéler sa consigne.

Comment ça marche
 question en français
        │
        ▼
 ┌─────────────────────────────┐  appels   ┌─────────────────────────┐
 │  Agent (smolagents)         │──────────▶│  5 outils Python testés │
 │  modèle : Claude Haiku 5.5  │           │  chercher_colonnes      │
 │  consigne + règles          │◀──────────│  decrire_colonne        │
 │  d'abstention               │  chiffres │  repartition            │
 └─────────────────────────────┘  agrégés  │  resume_numerique       │
        │                                  │  lignes                 │
        ▼                                  └────────────┬────────────┘
 { statut, valeur, justification }                      │ lecture locale
                                                        ▼
                                     données de santé (CSV, 4 271 patients)

L'agent suit la boucle Pensée → Action → Observation : il écrit un court code Python qui appelle ses outils, lit leur résultat, puis conclut. Il vise 2 étapes par question, et 1 étape quand il doit s'abstenir d'emblée (une question sur une ville, alors que le jeu de données n'en contient pas).

Les choix techniques, et pourquoi

1. Accès fermé aux données : souveraineté. L'agent ne reçoit pas le tableau. Il n'atteint les données qu'à travers les outils, qui renvoient des résultats agrégés. Aucune ligne de patient n'est envoyée à l'API du modèle. Seul l'outil lignes, prévu pour les questions sur un patient précis, renvoie quelques valeurs individuelles : 5 patients et 6 colonnes au plus.

2. Des outils qui portent la connaissance du domaine : justesse. Les pièges du jeu de données sont traités dans le code des outils, pas laissés au modèle :

9 et 999 signifient « non renseigné » ; ils sont exclus des calculs et le dénominateur est toujours donné ;
une cellule peut contenir plusieurs codes ("1, 3") : elle est découpée avant le comptage ;
trois puces (ISAC V1, ISAC V2, ALEX) ne mesurent pas les mêmes allergènes : un dosage n'est lu que pour les patients des puces qui le mesurent ;
52 dosages valent -1, une valeur non documentée : ils sont écartés, et l'outil le signale.

Chaque outil renvoie un message d'erreur qui dit quoi faire. Exemple : Colonne 'Gendre' inconnue. Colonnes proches : Gender. L'agent se corrige ainsi seul à l'étape suivante.

3. Un prompt système réécrit : frugalité. Le prompt par défaut de smolagents fait près de 10 000 caractères d'exemples génériques, renvoyés au modèle à chaque étape. Il est remplacé par un gabarit français court, centré sur le cas d'usage. Pour une même question, cela fait −43 % de caractères envoyés. S'y ajoutent un plafond de jetons de sortie (une question de l'agent de départ en avait produit 16 526) et une consigne qui fait grouper les appels d'outils.

4. Une abstention calibrée : honnêteté. S'abstenir à tort coûte autant qu'une erreur. L'agent s'abstient seulement quand les données ne permettent pas de conclure : information absente, lieu anonymisé, question de causalité, conseil médical individuel, prémisse fausse. Sur un petit effectif, il répond en signalant la fragilité de la conclusion. Cet équilibre a été trouvé en lisant les traces : une première version, trop prudente, s'abstenait sur des questions qui avaient une réponse.

5. Mesurer avant d'optimiser. Chaque changement a été évalué sur la même batterie de questions, avec des réponses attendues calculées indépendamment (dans un notebook Jupyter). Les outils sont couverts par 12 tests unitaires qui ne consomment aucun jeton.

Ce que l'analyse des données a révélé

Le travail sur l'agent a d'abord été un travail sur les données :

70 % des patients n'ont pas de type d'habitat renseigné (code 9). Un calcul naïf donne 23 % d'urbains, le bon calcul 74,8 %.
La population est jeune : âge médian 16 ans, de 0 à 102 ans. Toute généralisation à l'adulte demande de la prudence.
Le dictionnaire officiel ne donne ni unité ni seuil de positivité pour les dosages, et les puces ISAC et ALEX n'utilisent pas forcément la même échelle. L'agent ne parle donc jamais d'« allergique », seulement de « valeur > 0 ».
Des points restent ouverts et sont documentés dans le journal : le code 10 (« rongeur de compagnie ») pour 925 patients dans les cofacteurs, et une colonne Sensitization absente du dictionnaire.
Lancer le projet

Il faut git et uv, ainsi qu'une clé d'API Anthropic.

git clone https://github.com/WILLIAM04052005/allergylab-agent.git
cd allergylab-agent
uv run kit installer          # demande la clé d'API, rangée hors du dépôt
uv run kit controle           # vérifie données, clé et modèle
uv run kit agent "Quel est l'âge moyen des patients ?"

Pour évaluer l'agent et suivre les coûts :

uv run kit evaluer equipe/questions/lot1.toml   # justesse, abstention, frugalité
uv run kit bilan                                # coûts cumulés, par jour
uv run python -m pytest equipe -q               # tests des outils, sans appel au modèle
Organisation du dépôt
Dossier	Contenu
equipe/agent.py	l'agent : modèle, outils, accès fermé, plafond de sortie
equipe/consigne.md	la consigne : méthode, schéma des données, règles d'abstention
equipe/outils/	les 5 outils, leurs tests, les codes du dictionnaire officiel, le prompt système
equipe/questions/	la batterie de contrôle avec ses réponses attendues
equipe/interface/	une interface web locale : graphiques et questions à l'agent
JOURNAL.md	le journal de bord : ce qui a été essayé, mesuré et décidé, jour par jour
traces/	chaque question posée et chaque évaluation, avec étapes, jetons et coût
kit/	le harnais fourni pour la semaine : boucle, évaluation, traces
donnees/	le jeu de données et son dictionnaire, tels que publiés

Stack : Python 3.12, smolagents (Hugging Face), Claude Haiku 5.5 (Anthropic), pandas, pytest, uv.

Données et crédits
Données : jeu « Allergen Chip Challenge », Société Française d'Allergologie, DOI 10.60597/j5fe-g420, sous Licence Ouverte 2.0. Les fichiers de donnees/ sont reproduits sans modification.
Kit et harnais d'évaluation : fournis par l'encadrement de la semaine AllergyLab (dépôt du kit). Le kit documente aussi ce qu'il enregistre dans les traces : aucune donnée personnelle, aucune clé.
Agent, outils, consigne, analyse et interface : équipe 3.

Cet agent est un outil d'exploration statistique. Il ne fournit aucun avis médical.
# TD Gouvernance, profilage et qualité des données : dépôt de groupe

Ce dépôt est le vôtre pour tout le TD (5 séances). Il contient la pile Docker, vos fichiers de travail et les **livrables à remplir à chaque séance**. L'enseignant a un accès en lecture : il lit votre avancement ici, entre les séances.

## Démarrer (une fois, séance 1)

1. Créez votre dépôt à partir du modèle (bouton « Use this template », dépôt **privé**), nommé `td-qualite-GROUPE` (par exemple `td-qualite-g03`).
2. Ajoutez l'enseignant comme collaborateur en lecture (Settings, Collaborators) et chaque membre du groupe en écriture.
3. Clonez le dépôt, puis déposez le dossier `data/` fourni par l'enseignant à la racine du clone. Il est ignoré par git : ne le commitez jamais.
4. Lancez la pile : `docker compose up -d --build`, puis `docker exec dq_jupyter python pipelines/load_sources.py`.
5. Renseignez `livrables/00_equipe.md` avant la fin de l'ouverture de S1.

## Ce que vous rendez, séance par séance

| Séance | Livrable | Étiquette (tag) à poser à la fin |
|---|---|---|
| S1 | `livrables/S1_bronze_profilage.md` | `seance-1` |
| S2 | `livrables/S2_regles_great_expectations.md` | `seance-2` |
| S3 | `livrables/S3_integrite_soda.md` | `seance-3` |
| S4 | `livrables/S4_silver_gold.md` | `seance-4` |
| S5 | `livrables/S5_certificat_publication.md` | `seance-5` |
| Après S5 | `livrables/DOSSIER_GO_NOGO.md` | `rendu-final` |

Le modèle PowerPoint `livrables/Livrable_Groupe_TD_AssurConnect.pptx` reprend l'ensemble de ces livrables dans un seul fichier chartré (encadrés ambre « Attendu », zones à compléter). L'enseignant précise si le livrable noté est ce fichier ou les fichiers `.md` ; dans tous les cas, les chiffres viennent de vos mesures et les preuves du dépôt.

Deux fichiers vivent toute la durée du TD : `AVANCEMENT.md` (une ligne par story : statut et preuve) et `livrables/JOURNAL_DECISIONS.md` (chaque seuil, sévérité ou règle de survie choisi, avec le rôle qui l'a décidé).

## Comment remplir un livrable

Un livrable ne raconte pas ce que vous avez fait : il **prouve** ce que vous avez mesuré. Pour chaque constat :

1. **un chiffre mesuré**, avec la règle (RQ-xxx) et la couche (source, bronze, silver, gold) ;
2. **la preuve** : le fichier, la requête ou la commande qui reproduit ce chiffre, par un chemin du dépôt ;
3. **ce que cela change** : une conséquence ou une décision, attribuée à un rôle (Data Owner, Data Steward, ingénieur qualité).

Les emplacements à compléter sont marqués `[À COMPLÉTER]` ou `…`. Un livrable terminé n'en contient plus ; un livrable inachevé garde ses marqueurs, ce qui est normal et visible : ne les effacez pas pour faire propre.

Ne copiez pas les valeurs d'un autre groupe ni celles d'un tutoriel : l'enseignant compare vos chiffres à ceux d'une exécution de référence, et un écart expliqué vaut mieux qu'un chiffre juste sans preuve.

## Règles du dépôt

- **Un commit par morceau de travail**, par la personne qui l'a fait, avec un message de la forme `S2: RQ-003 nul, vide et blanc séparés (US-10)`. L'historique atteste la contribution de chacun.
- **À la fin de chaque séance** : commit, `git tag seance-N`, `git push --tags`. Vous pouvez compléter ensuite ; l'étiquette fixe l'état rendu en séance.
- Ne réécrivez jamais l'historique (`push --force`, `rebase` d'un commit déjà poussé).
- Ne commitez pas : `data/`, les sauvegardes SQL, les fichiers `.env`, les dossiers `uncommitted` de Great Expectations. Le `.gitignore` en exclut déjà la plupart ; la vérification automatique échoue si un fichier interdit passe.
- Notebooks : commitez-les avec leurs sorties, sans y laisser plus de vingt lignes de données brutes.
- Une modification de silver, de gold ou d'un fichier de checks se fait dans le code et se relance : on ne corrige jamais une couche à la main.

## Vérification automatique

À chaque `push`, un contrôle (`scripts/controle_livrable.py`, onglet Actions) affiche l'avancement de chaque livrable (marqueurs restants) et **échoue uniquement** si un fichier interdit est présent. Pour le lancer chez vous : `python3 scripts/controle_livrable.py`.

## Si vous êtes bloqués

La règle des vingt minutes : au-delà, appelez l'enseignant. Pour repartir d'un état propre de la base, l'enseignant peut utiliser un point de reprise ; vos fichiers (notebooks, checks, livrables) ne sont jamais touchés. Notez la reprise utilisée dans la section « Difficultés » du livrable de la séance.

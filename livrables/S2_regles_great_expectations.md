# S2 — Règles Great Expectations

G02 · lot `L-2026-10-01` · ingénieur qualité Maria Camila, Steward Ruth, Owner Iliana, rédaction Firdaouss.

## 1. Mesures par règle (US-10)

| Règle | Table Bronze | Testées | Échecs | Conformité | Sévérité / seuil |
|---|---|---|---|---|---|
| RQ-001 | crm_contrat | 100 000 | 800 | 99,20 % | BLOQUANTE / 100 % |
| RQ-002 | crm_contrat | 91 875 | 301 | 99,67 % | BLOQUANTE / 100 % |
| RQ-003 | crm_client | 49 978 | 5 995 | 88,00 % | AVERTISSEMENT / 98 % |
| RQ-005 | crm_client | 97 037 | 1 478 | 98,48 % | AVERTISSEMENT / 98 % |
| RQ-009 | crm_client | 100 000 | 200 | 99,80 % | BLOQUANTE / 100 % |
| RQ-010 | crm_contrat | 100 000 | 600 | 99,40 % | BLOQUANTE / 100 % |
| RQ-020 | crm_client | 100 000 | 0 | 100,00 % | BLOQUANTE / 100 % |
| RQ-020 | crm_contrat | 100 000 | 0 | 100,00 % | BLOQUANTE / 100 % |

Chaque test GE porte l’identifiant de sa règle dans `meta.rule_id`. Le notebook calcule une colonne `conforme`, puis GE vérifie son résultat. Les paramètres `DQ_SCHEMA`, `DQ_TABLE_CLIENT`, `DQ_TABLE_CONTRAT`, `DQ_TABLE_TYPE_CONTRAT` et `DQ_BATCH` permettent de choisir la couche, les tables et le lot, à condition que leur structure soit compatible.

Les huit suites sont enregistrées dans `reports/ge/gx/expectations/`, par table et par règle. Le notebook `notebooks/S2_US10_regles_en_tests.ipynb` contient les calculs métier, sauvegarde les suites et vérifie leur relecture. Les suites et les calculs du notebook s’utilisent ensemble. Résultats : `reports/S2_execution.json`.

Les populations testées sont précisées pour éviter de comparer des taux qui ne portent pas sur les mêmes lignes. RQ-003 compte NULL, vide et espaces comme des absences : 5 995 sur 49 978 souscripteurs. Pour RQ-005, Soda sur les pays exactement FR mesure 1 456 échecs sur 95 437 lignes (98,47 %). GE, après normalisation FR/FRANCE, mesure 1 478 sur 97 037 (98,48 %). La normalisation complémentaire F/Frnace en S4 donne 1 493 sur 98 037 (98,48 %). RQ-002 porte sur les personnes physiques évaluables ; les références absentes sont contrôlées par les règles d’intégrité.

Les résultats Silver sont dans `reports/executions/corrections_s2_s5_20261115/silver_mesures.json`, avec huit suites dans `reports/ge/silver/expectations/`. Le contrôle client reste limité à la source CRM pour conserver un périmètre comparable. La commande `python scripts/valider_notebooks.py --silver --date-comparaison 2026-11-15` utilise un historique temporaire et conserve les résultats Bronze. La date de comparaison peut être fixée avec `DQ_COMPARISON_DATE`.

## 2. Lignes en échec (US-11)

Export : `livrables/preuves/S2_US11_echecs_complets.csv` (**9 374 occurrences**, pas nécessairement autant de clients distincts). Échantillon déterministe : `livrables/preuves/S2_US11_echantillon_commente.csv`, **20 lignes**.

| Règle | Lignes de l’échantillon |
|---|---|
| RQ-001 | 4 |
| RQ-002 | 4 |
| RQ-003 | 3 |
| RQ-005 | 3 |
| RQ-009 | 3 |
| RQ-010 | 3 |

Chaque ligne de l’échantillon indique la famille d’erreur, le constat, la cause probable et une action avec son destinataire. Les causes restent à confirmer par le métier. Le notebook `notebooks/S2_US11_lignes_en_echec.ipynb` permet de produire les exports.

## 3. Âge au début du contrat (US-13)

Population : 91 875 souscripteurs personnes physiques évaluables. **301** étaient mineurs au début du contrat ; **143** sont mineurs à la date de comparaison **15/11/2026** ; **158** classifications divergent. La comparaison se paramètre avec `DQ_COMPARISON_DATE` ; le jour d’exécution est utilisé par défaut et est affiché.

Cas réel `CT0000387` : naissance 28/09/1996, début 01/09/2014, **17 ans au début**, **30 ans au 15/11/2026**. Une majorité actuelle ne répare pas l’échec RQ-002 historique. Preuve : `notebooks/S2_g02.ipynb`, `reports/S2_analyse_reference.json`.

## 4. Référence par dimension (US-15)

| Dimension | Moyenne des couples règle/table | Règle la plus faible |
|---|---|---|
| Complétude | 88,00 % | RQ-003 |
| Cohérence | 99,20 % | RQ-001 |
| Validité | 99,34 % | RQ-005 |
| Unicité | 100,00 % | RQ-020 |

La moyenne donne le même poids à chaque couple règle/table de l’exécution US-10 référencée dans `reports/S2_execution.json`. Les huit mesures sont utilisées ensemble, pour le même lot et les mêmes tables. Cette moyenne ne représente pas la part de clients sans défaut et ne compense pas une règle bloquante en échec.

La lecture et l’écriture utilisent des connexions distinctes. Les huit mesures ont été écrites puis relues dans un schéma de validation temporaire, nettoyé en fin d’exécution. Cette vérification préserve l’historique du lot certifié dans `dq.dq_history`.

## 5. Bilan

- [x] Identifiant de règle dans chaque expectation et suites persistées/rechargées.
- [x] Export complet et échantillon de vingt lignes régénérés.
- [x] Calcul d’âge et cas divergent réexécutés.
- [x] Historisation et relecture testées dans un schéma isolé, nettoyé.
- [x] Trois notebooks S2 exécutés de bout en bout avec sorties.

Les erreurs présentes dans Bronze décrivent les défauts des données reçues. Le Data Owner a validé les seuils et la population du contrôle d’âge dans D-08. Les temps de traitement ne sont pas disponibles.

## 6. Contrôles Gold

US-10 vérifie les sept règles et huit couples règle/table sur `gold.client_unique` et `gold.contrat_certifie`. Les résultats sont dans `reports/S2_execution_gold.json` et les suites dans `reports/ge/gold/expectations/`. RQ-003 porte sur les statuts ACTIF, INACTIF et A_REVOIR ; RQ-009 contrôle les cinq statuts Gold. RQ-002 calcule l’âge au début du contrat pour les personnes physiques et signale les références, natures ou dates manquantes. La commande `python scripts/valider_notebooks.py --gold --date-comparaison 2026-11-15` vérifie cette couche dans un historique temporaire, sans changer les mesures certifiées.
# Avancement du groupe

Groupe : G02 · lot `L-2026-10-01` · date de référence : 01/10/2026

Le tableau reprend les stories réalisées et les fichiers qui permettent de vérifier notre travail. Les remarques précisent les résultats et les points qui restent à suivre.

| Séance | Story | Intitulé | Statut | Preuve (chemin ou commande) | Remarque |
|---|---|---|---|---|---|
| S1 | US-01 | Inventorier les sources | Fait | notebooks/S1_g02.ipynb ; reports/S1_ingenieur_qualite.json | Les sept tables CRM et CIF sont inventoriées. |
| S1 | US-02 | Alimenter bronze | Fait | notebooks/S1_g02.ipynb ; reports/S1_ingenieur_qualite.json | Les données sources sont copiées avec les métadonnées du lot. |
| S1 | US-03 | Porte B : réconcilier source et bronze | Fait | reports/S1_ingenieur_qualite.json | Les comptages et sommes de contrôle ne présentent aucun écart. |
| S1 | US-04 | Dictionnaire du CIF | Fait | notebooks/S1_US04_dictionnaire_cif.ipynb | Les dix colonnes anonymes du CIF sont décrites et justifiées. |
| S1 | US-06 | Profil de crm.client | Fait | notebooks/S1_US06_profil_crm_client.ipynb ; reports/S1_US06_profil_crm_client.html | Le profil présente les valeurs manquantes, les doublons et les anomalies. |
| S1 | US-07 | Motifs code postal, téléphone, pays | Fait | notebooks/S1_US07_motifs_regex.ipynb | Les formats des codes postaux, téléphones et pays ont été vérifiés. |
| S1 | US-09 | Trois définitions du client actif | Fait | notebooks/US-09_client_actif.ipynb ; reports/S1_US09_reference.json | Les écarts entre les trois définitions sont expliqués à la date du lot. |
| S2 | US-10 | Règles en tests Great Expectations | Fait | notebooks/S2_US10_regles_en_tests.ipynb ; reports/S2_execution.json ; reports/S2_execution_gold.json ; reports/ge/gold/expectations/ | Les sept règles sont testées sur Bronze, Silver et Gold ; les suites sont enregistrées. |
| S2 | US-11 | Lignes en échec | Fait | livrables/preuves/S2_US11_echantillon_commente.csv | Un échantillon de vingt lignes présente les familles d’erreurs et les actions proposées. |
| S2 | US-13 | Âge à la date de début du contrat | Fait | notebooks/S2_g02.ipynb ; reports/S2_analyse_reference.json | L’âge est calculé au début du contrat et comparé à l’âge au jour de validation. |
| S2 | US-15 | Mesure de référence sur bronze | Fait | reports/S2_execution.json ; reports/S2_analyse_reference.json | Les mesures de référence sont enregistrées et relues dans un historique de validation séparé. |
| S3 | US-12 | Checks Soda, une source par couche | Fait | soda/checks/ ; reports/executions/conformite_prof_20261115/soda_bronze.json | Les contrôles Bronze sont filtrés par lot ; les anomalies du brut restent visibles. |
| S3 | US-16 | Clés étrangères | Fait | notebooks/S3_g02.ipynb | Les références absentes sont comptées pour chaque relation. |
| S3 | US-17 | Valeur sentinelle | Fait | notebooks/S3_g02.ipynb ; livrables/JOURNAL_DECISIONS.md | La valeur 0 est expliquée ; les vrais orphelins sont distingués des sentinelles. |
| S3 | US-18 | Statuts de personne | Fait | notebooks/S3_g02.ipynb | Les écarts de statut et leur traitement sont documentés dans le journal. |
| S3 | US-19 | Période de garantie | Fait | notebooks/S3_g02.ipynb | Les dates des sinistres sont comparées aux périodes de garantie. |
| S3 | US-14 | Définition unique du client actif | Fait | queries/S3_US14_client_actif.sql ; notebooks/S3_g02.ipynb | La même définition donne 38 049 clients actifs en Bronze pour les trois directions. |
| S4 | US-21 | Silver : standardiser | Fait | notebooks/S4_g02.ipynb ; reports/S4_modifications.json | Les formats sont harmonisés sans modifier les données Bronze. |
| S4 | US-22 | Quarantaine | Fait | reports/S4_correctifs_synthese.json | Les lignes écartées sont conservées avec leur motif de rejet. |
| S4 | US-23 | Porte S : re-mesurer sur silver | Fait | reports/S4_couverture.json | La conservation Bronze = Silver + rejets est vérifiée ; les règles sont remesurées. |
| S4 | US-24 | Dédoublonnage | Fait | reports/S4_correctifs_synthese.json ; reports/S4_RQ019_resolution.json | Le rapprochement est réalisé ; 377 CLI restent exclus et 23 consolidations attendent une confirmation humaine. |
| S4 | US-25 | Golden record | Fait | reports/S4_traces_corrigees.json ; reports/AUDIT_survie_contre_exemple.json | Les valeurs retenues et leurs sources sont expliquées ; les limites de la règle de survie restent indiquées. |
| S4 | US-27 | Gold et client actif unique | Fait | reports/S4_RQ019_resolution.json ; reports/S5_certificat_final.json | Gold contient 36 041 clients actifs ; les identités en quarantaine restent hors publication. |
| S4 | US-28 | Traçabilité de trois données | Fait | pipelines/S4_US28_tracabilite.sql ; reports/S4_traces_corrigees.json | Les trois exemples remontent de Gold aux lignes sources avec le lot. |
| S5 | US-29 | Historique des mesures | Fait | reports/S5_export_steward.json | Les mesures par règle, table et couche sont conservées dans l’historique. |
| S5 | US-30 | Courbes d'évolution | Fait | notebooks/S5_data_steward.ipynb ; reports/S5_US30_courbe.png | Les courbes montrent l’évolution par dimension ; un exemple sur données fictives illustre un plateau puis une progression. |
| S5 | US-31 | Certificat de qualité | Fait | reports/S5_certificat_final.json | Le certificat est GO : 59 contrôles bloquants conformes sur 59, couvrant 18 règles. |
| S5 | US-32 | Publication vers le CRM | Fait | reports/S5_preuves_finales.json | Les trois tables sont chargées ; les volumes et empreintes concordent avec Gold. |
| S5 | US-34 | Catalogue, propriétaires, lineage | Fait | catalogue/catalogue.yml ; catalogue/gold_client_unique.md ; catalogue/app.py ; tests/test_catalogue.py | Le catalogue présente les responsables, les définitions, les règles et les liens vers les sources. |
| S5 | US-35 | Dossier go/no-go | Fait | livrables/DOSSIER_GO_NOGO.md ; livrables/Dossier_GO_NO_GO_AssurConnect_G02.pdf | Le dossier rassemble la recommandation, les preuves, les réserves et la décision du Data Owner. |

Stories d'extension (facultatives) : US-05, US-08, US-20, US-26, US-33.

Le rapprochement BAN de l’US-26 a été traité dans S4, mais la cible de 2 % d’adresses non rapprochées n’est pas atteinte : 7 997 adresses restent isolées. Les autres extensions ne sont pas terminées.

Les réserves sur les identités restent à instruire : Firdaouss suit la revue des 23 consolidations et des 377 CLI exclus, avec arbitrage de Ruth pour les cas sans preuve. L’échéance du dossier est le 20/12/2026.

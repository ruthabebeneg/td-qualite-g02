# Avancement G02

État documentaire consolidé le 15/11/2026. « Fait » désigne le livrable et sa preuve, pas l’absence de toute réserve métier ni la confirmation humaine de toutes les identités. Les exécutions historiques et nouvelles sont distinguées dans les livrables.

| Séance | Story | Intitulé | Statut | Preuve | Remarque |
|---|---|---|---|---|---|
| S1 | US-01 | Inventorier les sources | Fait | notebooks/S1_g02.ipynb ; reports/S1_ingenieur_qualite.json |  |
| S1 | US-02 | Alimenter Bronze | Fait | notebooks/S1_g02.ipynb ; reports/S1_ingenieur_qualite.json |  |
| S1 | US-03 | Réconciliation porte B | Fait | reports/S1_ingenieur_qualite.json |  |
| S1 | US-04 | Dictionnaire CIF | Fait | notebooks/S1_US04_dictionnaire_cif.ipynb |  |
| S1 | US-06 | Profil CRM | Fait | notebooks/S1_US06_profil_crm_client.ipynb ; reports/S1_US06_profil_crm_client.html |  |
| S1 | US-07 | Motifs et regex | Fait | notebooks/S1_US07_motifs_regex.ipynb |  |
| S1 | US-09 | Trois définitions du client actif | Fait | notebooks/US-09_client_actif.ipynb ; reports/S1_US09_reference.json |  |
| S2 | US-10 | Règles GE | Fait | notebooks/S2_US10_regles_en_tests.ipynb ; reports/S2_execution.json |  |
| S2 | US-11 | Lignes en échec | Fait | livrables/preuves/S2_US11_echantillon_commente.csv |  |
| S2 | US-13 | Âge au début du contrat | Fait | notebooks/S2_g02.ipynb ; reports/S2_analyse_reference.json |  |
| S2 | US-15 | Référence Bronze | Fait | reports/S2_execution.json ; reports/S2_analyse_reference.json | Validation S2 en schéma isolé ; historique nominal préservé |
| S3 | US-12 | Checks Soda | Fait | soda/checks/ ; reports/AUDIT_soda.json |  |
| S3 | US-16 | Clés étrangères | Fait | notebooks/S3_g02.ipynb |  |
| S3 | US-17 | Sentinelle | Fait | notebooks/S3_g02.ipynb ; livrables/JOURNAL_DECISIONS.md |  |
| S3 | US-18 | Statuts de personne | Fait | notebooks/S3_g02.ipynb |  |
| S3 | US-19 | Période de garantie | Fait | notebooks/S3_g02.ipynb |  |
| S3 | US-14 | Client actif unique | Fait | queries/S3_US14_client_actif.sql ; notebooks/S3_g02.ipynb |  |
| S4 | US-21 | Standardiser Silver | Fait | notebooks/S4_g02.ipynb ; reports/S4_modifications.json |  |
| S4 | US-22 | Quarantaine | Fait | reports/S4_correctifs_synthese.json |  |
| S4 | US-23 | Porte S | Fait | reports/S4_couverture.json |  |
| S4 | US-24 | Dédoublonnage | Fait | reports/S4_correctifs_synthese.json ; reports/S4_RQ019_resolution.json | Revue de 377 CLI et 23 consolidations toujours ouverte |
| S4 | US-25 | Golden record | Fait | reports/S4_traces_corrigees.json ; reports/AUDIT_survie_contre_exemple.json | Historique + contre-exemple synthétique ; revue humaine distincte |
| S4 | US-27 | Gold et client actif | Fait | reports/S4_RQ019_resolution.json ; reports/S5_certificat_final.json | Revue de 377 CLI et 23 consolidations toujours ouverte |
| S4 | US-28 | Trois traces | Fait | pipelines/S4_US28_tracabilite.sql ; reports/S4_traces_corrigees.json |  |
| S5 | US-29 | Historique | Fait | reports/S5_export_steward.json |  |
| S5 | US-30 | Courbes | Fait | notebooks/S5_data_steward.ipynb ; reports/S5_US30_courbe.png |  |
| S5 | US-31 | Certificat | Fait | reports/S5_certificat_final.json |  |
| S5 | US-32 | Publication CRM | Fait | reports/S5_preuves_finales.json |  |
| S5 | US-34 | Catalogue et lineage | Fait | catalogue/catalogue.yml ; catalogue/gold_client_unique.md |  |
| S5 | US-35 | Dossier de décision | Fait | livrables/DOSSIER_GO_NOGO.md ; livrables/Dossier_GO_NO_GO_AssurConnect_G02.pdf |  |

Extensions : US-05, US-08 et US-20 non revendiquées complètes ; US-26 rapprochement BAN traité dans S4, sans prétendre atteindre la cible source de 2 % (7,997 % d’adresses isolées) ; US-33 orchestration non retenue.

Remise Git : le tag historique `seance-3` est attesté et le tag local `rendu-final` désigne le commit de corrections du 15/11. Les autres tags de séance ne sont pas annoncés comme posés/poussés ; aucune référence historique arbitraire n’a été créée. Le tag final reste à pousser. La publication externe et la visibilité du dépôt restent à vérifier lors de la remise.

# Dossier go/no-go — G02

À l’attention de la Directrice Générale d’AssurConnect · 15 novembre 2026 · lot `L-2026-10-01`.

## 1. Recommandation

**GO sous conditions pour le seul périmètre certifié et déjà publié le 12/11/2026.** Garder les 377 CLI en quarantaine hors du CRM jusqu’à preuve d’identité. La recommandation n’autorise pas l’ajout automatique des lignes exclues.

Trois raisons : **59 contrôles conformes sur 59**, couvrant 18 règles préalables sur Bronze/Silver/Gold ; **120 673 clients, 95 822 contrats et 88 824 sinistres** chargés sans écart ; les réserves sont identifiées et conservées : **377 CLI exclus, 1 569 statuts A_REVOIR et 5 190 téléphones manquants**.

## 2. Preuves

Certificat `S5-d7c760617b538e9240c8541a4f7`, GO, empreinte Gold `a62b0b820e96225b76b20fa7aa0f5b3d4b84841a1c7770801e4e7fcb3ddd1667` ; approbation Ruth, Data Owner, 12/11/2026 : `reports/S5_VALIDATION_DATA_OWNER.json`. Réconciliation après commit : `reports/S5_preuves_finales.json`. RQ-025 est contrôlée après chargement, séparément du certificat préalable.

Mesures par règle et couche et courbe : `S5_certificat_publication.md`, `reports/S5_US30_courbe.png`, `reports/S5_export_steward.json`. RQ-003 : 88,00 / 88,05 / 89,26 %, cible 98 % non atteinte. Les règles bloquantes requises du périmètre retenu atteignent 100 % ; cela ne signifie pas que toutes les données reçues sont correctes.

Trois traces : Société Meunier CLI-033864 ← trois CRM et un CIF ; CP CLI-000069 : 1500 → 01500 ; adresse sinistre SIN0000008 : Platanees → Platanes, BAN012063. Preuves ligne à ligne : `reports/S4_traces_corrigees.json`, requête `pipelines/S4_US28_tracabilite.sql`.

## 3. Écarts et périmètres

| Écart | Chiffre | Conséquence / action |
|---|---|---|
| RQ-016 | 1 569 / 48 322 ; 96,75 % < 98 % | Steward : vérifier les anciens souscripteurs sans contrat certifié |
| RQ-003 | 5 190 / 48 322 ; 89,26 % | Vérifier les autres canaux de contact ; ne pas inventer de téléphone |
| RQ-006 | 553 couples CP/commune ; 99,53 % | Contrôle métier avant correction |
| RQ-019 | 377 CLI, 396 identifiants, 337 contrats et 332 sinistres associés | Hors publication jusqu’à preuve d’identité |
| Rejets S | 444 clients CRM, 1 400 contrats, 7 997 sinistres | Correction à la source, conservation tracée |
| Exclusions G seules | 2 778 contrats et 3 179 sinistres, dont dépendances RQ-019 | Non publiés depuis Silver |
| Total exclu depuis Bronze | **4 178 contrats et 11 176 sinistres** | Somme des rejets S et exclusions G, sans double comptage |
| Réserve de fusion | 23 consolidations techniques non confirmées humainement | Revue Steward ; pas de prétention de vérité métier |

Conventions déjà décidées : référence du lot D-05/D-06, sentinelle D-02, renouvellement D-12, statut historique D-17. Restent à instruire les cas individuels, l’éventuel produit T13 et la fraîcheur des attributs faute d’horodatage source. Une convention validée n’est pas une hypothèse encore sans décision.

## 4. Décision et responsables

La Directrice Générale décide de la migration. Ruth, Data Owner, a approuvé le certificat lié à ce contenu ; Firdaouss, Steward S5, suit les écarts ; Iliana, ingénieure qualité S5, réalise contrôles et publication. Maria Camila tient le dossier.

Seuils : bloquantes 100 % et avertissements 98 % (D-07/D-08/D-22), rapprochement auto ≥ 90 et revue 75–90 (D-14), adresses 90 avec garde-fous (D-16), survie D-15, publication D-23/D-25/D-27.

| Condition avant réintégration ou extension | Responsable | Échéance du dossier existant |
|---|---|---|
| Revue humaine des 23 consolidations | Firdaouss, Data Steward | 20/12/2026 |
| Instruction individuelle des 377 CLI exclus | Firdaouss, Data Steward ; arbitrage Ruth | 20/12/2026 |

Signature enregistrée : **Ruth, Data Owner, 12/11/2026**, dans le fichier d’approbation existant. La correction documentaire ne constitue pas une nouvelle signature ni une décision de la Directrice Générale.

Annexes : `00_equipe.md`, `JOURNAL_DECISIONS.md`, `../AVANCEMENT.md`, `S1_bronze_profilage.md`, `S2_regles_great_expectations.md`, `S3_integrite_soda.md`, `S4_silver_gold.md`, `S5_certificat_publication.md`. Version PDF courte : `Dossier_GO_NO_GO_AssurConnect_G02_corrige.pdf`.

Support oral synchronisé : `Soutenance_AssurConnect_G02.pptx`. Répartition et durées proposées à confirmer par le groupe.

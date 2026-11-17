# S1 — Bronze et profilage

Groupe G02 · lot `L-2026-10-01` · date de référence : 01/10/2026 · rôles : `00_equipe.md`.

## 1. Inventaire (US-01)

| Source | Table | Lignes | Clé primaire | Observation |
|---|---|---|---|---|
| crm | client | 100 000 | client_id | 0 clé nulle ; 0 doublon |
| crm | contrat | 100 000 | contrat_id | 0 clé nulle ; 0 doublon |
| crm | sinistre | 100 000 | sinistre_id | 0 clé nulle ; 0 doublon |
| crm | type_contrat | 12 | code_type | 0 clé nulle ; 0 doublon |
| cif | clients | 40 000 | column0 | 0 clé nulle ; 0 doublon |
| cif | compte | 45 000 | column0 | 0 clé nulle ; 0 doublon |
| cif | pays | 250 | code_pays | 0 clé nulle ; 0 doublon |

Preuve : `notebooks/S1_g02.ipynb`, `reports/S1_ingenieur_qualite.json`. Total : **385 262 lignes**, sept tables ; aucune des sept clés n’est absente. Ingénieur qualité : Iliana.

## 2. Bronze et porte B (US-02/03)

Lecture SQL sous `reader`, avec `coerce_float=False` pour préserver les décimaux. Conversion explicite et ajout de `_batch_id`, `_source_system`, `_ingested_at`, `_row_hash`. La relance du même lot conserve les valeurs et volumes sans doublon ; les identifiants techniques et horodatages peuvent être renouvelés, ce qui interdit une relance amont sur un lot déjà certifié sans reconstruire ses dépendances.

| Table Bronze | Source | Bronze | Écart comptage | Écart somme |
|---|---|---|---|---|
| crm_client | 100 000 | 100 000 | 0 | 0 |
| crm_contrat | 100 000 | 100 000 | 0 | 0 |
| crm_sinistre | 100 000 | 100 000 | 0 | 0 |
| crm_type_contrat | 12 | 12 | 0 | 0 |
| cif_clients | 40 000 | 40 000 | 0 | 0 |
| cif_compte | 45 000 | 45 000 | 0 | 0 |
| cif_pays | 250 | 250 | 0 | 0 |

**RQ-021 couvre comptages et sommes de contrôle ; RQ-022 couvre les quatre métadonnées.** Les sept vérifications RQ-022 ont zéro échec ; 14 mesures S1 sont historisées.

| Épreuve | Résultat | Preuve |
|---|---|---|
| Même lot relancé | 0 doublon ajouté, contenus et volumes identiques | `reports/S1_ingenieur_qualite.json`, relance |
| Contenu altéré sur copie | Comptage inchangé, écart somme −3 465 902 982, porte refusée ; copie supprimée | même rapport, epreuve_copie |
| Décimale 184.10 | Lecture flottante 184.1 ; lecture Decimal 184.10 préservée | même rapport, conversion |

## 3. Profil et motifs (US-06/07)

| Constat Bronze CRM | Mesure | Conséquence |
|---|---|---|
| Courriels nuls | 19 365 / 100 000 | Ne pas promettre un canal de contact disponible |
| Téléphones nuls | 5 999 / 100 000 | Distinguer nuls des 4 000 vides/blancs |
| Personnes morales | 4 277 ; nom/prénom/naissance absents | Manquants attendus, pas automatiquement erreurs |
| Identité nom+prénom+naissance répétée | 2 156 occurrences signalées | Candidats de rapprochement, pas preuve de même personne |
| Client créé avant naissance | 3 476 | Anomalie de dates à instruire, non révélée par une simple complétude |

Preuves : `notebooks/S1_US06_profil_crm_client.ipynb` et `reports/S1_US06_profil_crm_client.html`. Le rapport HTML fournit les constats de complétude ; les rapprochements et comparaisons métier sont confirmés par les requêtes du notebook.

| Motif | Conformes | Non conformes | Périmètre |
|---|---|---|---|
| CP selon pays | 98 480 | 1 520 | 100 000 lignes ; pas de regex française appliquée aux CP étrangers |
| Téléphone strict | 66 470 | 33 530 | 100 000 lignes, manquants compris |
| Téléphone tolérant | 87 741 | 12 259 | 100 000 lignes, diagnostic de formats |
| Pays regex + ISO | 96 950 | 3 050 | 100 000 lignes |

US-07 : `notebooks/S1_US07_motifs_regex.ipynb`. **A01 : 1 493 CP français à quatre chiffres**, restaurables par zéro initial (`1500` → `01500`). Les codes postaux étrangers légitimes sont distingués des anomalies françaises. Les motifs sont exprimés avec `9` chiffre et `A` lettre.

## 4. Dictionnaire CIF (US-04)

| Colonne | Nom proposé | Type cible | Justification mesurée |
|---|---|---|---|
| column0 | identifiant_cif | VARCHAR(7) | 40 000 distincts, 0 nul |
| column1 | nom_raison_sociale | VARCHAR(80) | 731 distincts, 0 nul ; formes juridiques observées |
| column2 | prenom | VARCHAR(80) | 180 distincts ; 645 nuls associés aux naissances nulles |
| column3 | date_naissance | DATE | JJ/MM/AAAA ; 23 795 jours > 12 ; 0 date invalide |
| column4 | adresse | VARCHAR(120) | 9 811 distinctes, longueurs 11–31 |
| column5 | code_postal | VARCHAR(10) | 188 distincts ; longueurs 4–8, conserver en texte |
| column6 | commune | VARCHAR(80) | 172 distinctes |
| column7 | pays_iso | CHAR(2) | 9 valeurs à deux lettres |
| column8 | telephone | VARCHAR(20) | 33 676 distincts ; 6 324 nuls ; 10 caractères sur les renseignés |
| column9 | courriel | VARCHAR(120) | 21 128 distincts ; 18 872 nuls ; 0 format invalide observé |

Preuve : `notebooks/S1_US04_dictionnaire_cif.ipynb`. Les types cibles sont proposés ; Bronze conserve les valeurs brutes. Data Steward : Firdaouss.

## 5. Trois définitions du client actif (US-09)

Date commune : **01/10/2026**, cotisation depuis le **01/07/2026**, lot filtré dans les lectures.

| Direction | Définition | Clients | Écart à CD-001 |
|---|---|---|---|
| Commerciale | Souscripteurs présents dans les contrats | 50 508 | 12 459 |
| Sinistres | Contrat en cours à la référence | 44 116 | 6 067 |
| Risques | Contrat en cours et cotisation sur trois mois calendaires | 38 049 | 0 |

Preuve réexécutée : `notebooks/US-09_client_actif.ipynb`, `reports/S1_US09_reference.json`. Les trois définitions portent sur des populations différentes. Le Data Owner a retenu la définition commune CD-001 dans les décisions D-05/D-06, pour comparer les résultats à date et périmètre identiques.

## 6. Bilan

- [x] Sept tables Bronze et quatre métadonnées, porte B sans écart : preuves S1.
- [x] Relance et écart volontaire démontrés sur copie : rapport S1.
- [x] RQ-021/RQ-022 historisées : rapport S1 et historique nominal.
- [x] US-09 réexécutée sur le lot correct : rapport du 15/11.

Les décimaux sont lus sans conversion flottante afin de préserver les valeurs, par exemple `184.10`. Les extensions US-05 et US-08 ne font pas partie des travaux terminés. Les temps de traitement ne sont pas disponibles.

# Avancement du groupe

Groupe : [À COMPLÉTER]

Mettez à jour ce tableau à chaque fin de séance (et dès qu'une story change d'état). Statut : `À faire`, `En cours`, `Fait`, `Bloqué`. La preuve est un chemin du dépôt (notebook, fichier de checks, requête) ou une commande ; pas de preuve, pas de `Fait`.

| Séance | Story | Intitulé | Statut | Preuve (chemin ou commande) | Remarque |
|---|---|---|---|---|---|
| S1 | US-01 | Inventorier les sources | À faire | … | |
| S1 | US-02 | Alimenter bronze | À faire | … | |
| S1 | US-03 | Porte B : réconcilier source et bronze | À faire | … | |
| S1 | US-04 | Dictionnaire du CIF | À faire | … | |
| S1 | US-06 | Profil de crm.client | À faire | … | |
| S1 | US-07 | Motifs code postal, téléphone, pays | À faire | … | |
| S1 | US-09 | Trois définitions du client actif | À faire | … | |
| S2 | US-10 | Règles en tests Great Expectations | À faire | … | |
| S2 | US-11 | Lignes en échec | À faire | … | |
| S2 | US-13 | Âge à la date de début du contrat | À faire | … | |
| S2 | US-15 | Mesure de référence sur bronze | À faire | … | |
| S3 | US-12 | Checks Soda, une source par couche | À faire | … | |
| S3 | US-16 | Clés étrangères | À faire | … | |
| S3 | US-17 | Valeur sentinelle | À faire | … | |
| S3 | US-18 | Statuts de personne | À faire | … | |
| S3 | US-19 | Période de garantie | À faire | … | |
| S3 | US-14 | Définition unique du client actif | À faire | … | |
| S4 | US-21 | Silver : standardiser | En cours | notebooks/S4_g02.ipynb ; reports/S4_correctifs_synthese.json ; reports/S4_couverture.json | Spark réel, normalisation et nature PP/PM explicites ; proposition non acceptée. |
| S4 | US-22 | Quarantaine | En cours | notebooks/S4_g02.ipynb ; reports/S4_correctifs_synthese.json ; reports/S4_couverture.json | Conservation par origine et deux rejeux prouvés ; validation Owner en attente. |
| S4 | US-23 | Porte S : re-mesurer sur silver | En cours | notebooks/S4_g02.ipynb ; reports/S4_correctifs_synthese.json ; reports/S4_couverture.json | Couverture CRM/CIF/gold et limites explicites ; aucune conformité exhaustive revendiquée. |
| S4 | US-24 | Dédoublonnage | En cours | notebooks/S4_g02.ipynb ; reports/S4_correctifs_synthese.json ; reports/S4_couverture.json  reports/S4_steward_index.json ; reports/S4_steward_synthese.json ;| 121073 identités ; précision 1.0, rappel 0.95 sur 200 paires ; revue obligatoire ambiguïtés.  Instruction Steward réalisée : 432 paires et 391 signatures ; 5 rapprochements appuyés sur labels proposés, confirmation des conflits et décisions Owner EN_ATTENTE.|
| S4 | US-25 | Golden record | En cours | notebooks/S4_g02.ipynb ; reports/S4_correctifs_synthese.json ; reports/S4_couverture.json  reports/S4_steward_index.json ; reports/S4_steward_synthese.json ;| 43734 entrées de revue ; contacts invalides exclus, survie proposée EN_ATTENTE.  Instruction réalisée : 2153 égalités et 41149 absences, actions par source/règle/couche ; 5212 défauts RQ-003/GOLD, 715 RQ-004/SILVER, 1054 RQ-008/SILVER (recouvrements possibles), email GOLD NULL non applicable ; 373 téléphones invalides ASSURE/PROSPECT P2. Réponses métier EN_ATTENTE ; index atomique de la génération courante.|
| S4 | US-26 | Adresses de sinistre et BAN | En cours | notebooks/S4_g02.ipynb ; reports/S4_correctifs_synthese.json ; reports/S4_couverture.json  reports/S4_steward_index.json ; reports/S4_steward_synthese.json ;| 3958 corrections, 7997 résidus (7.997 %) ; cible 2 % non atteinte.  Instruction réalisée : 1982 numéros absents, 3939 couples non couverts BAN, 2020 numéros non couverts, 56 voies sous seuil ; pièces métier EN_ATTENTE.|
| S4 | US-27 | Gold et client actif unique | En cours | notebooks/S4_g02.ipynb ; reports/S4_correctifs_synthese.json ; reports/S4_couverture.json  reports/S4_steward_index.json ; reports/S4_steward_synthese.json ;| 36165 actifs ; A_REVOIR et défauts RQ016 visibles ; gold NON ACCEPTE.  Instruction réalisée : 1552 statuts, dont 969 sans contrat bronze, 157 sans contrat silver et 426 silver non certifiés ; aucun statut modifié.|
| S4 | US-28 | Traçabilité de trois données | En cours | notebooks/S4_g02.ipynb ; reports/S4_correctifs_synthese.json ; reports/S4_couverture.json | Trois traces et lineage externe par origine/lot ; cardinalité xref sans anomalie, pas preuve exhaustive des personnes. |
| S5 | US-29 | Historique des mesures | À faire | … | |
| S5 | US-30 | Courbes d'évolution | À faire | … | |
| S5 | US-31 | Certificat de qualité | À faire | … | |
| S5 | US-32 | Publication vers le CRM | À faire | … | |
| S5 | US-34 | Catalogue, propriétaires, lineage | À faire | … | |
| S5 | US-35 | Dossier go/no-go | À faire | … | |

Stories d'extension (facultatives) : US-05, US-08, US-20, US-26, US-33. Ajoutez une ligne si vous les traitez.

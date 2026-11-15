# S4 — Silver, Gold et traçabilité

G02 · lot `L-2026-10-01` · IQ Firdaouss, Steward Iliana, Owner Ruth, rédaction Maria Camila.

## 1. Standardisation et conservation (US-21/22)

Exécuteur corrigé : `notebooks/S4_g02.ipynb`. Les notebooks `S4_silver.ipynb` et `S4_gold.ipynb` conservent les étapes historiques ; la version intégrée porte les garde-fous complémentaires.

| Traitement CRM | Lignes modifiées | Garde-fou |
|---|---:|---|
| Adresse | 1 793 | Ne pas inventer numéro ou commune |
| CP | 1 493 | Texte, zéro initial uniquement quand justifié |
| Pays | 2 220 | Correspondance explicite, inconnu en quarantaine |
| Téléphone | 25 170 | Normaliser sans créer de contact |
| Rôle | 544 | Contrat factuel et convention métier |

Ces effectifs ne s’additionnent pas : une ligne peut subir plusieurs transformations. CIF : 39 355 dates converties et 159 identités modifiées. Preuve : `reports/S4_modifications.json` et `reports/S4_correctifs_synthese.json`.

| Entité | Bronze | Silver | Rejets S | Écart |
|---|---|---|---|---|
| client (crm) | 100 000 | 99 556 | 444 | 0 |
| client (cif) | 40 000 | 40 000 | 0 | 0 |
| contrat (crm) | 100 000 | 98 600 | 1 400 | 0 |
| sinistre (crm) | 100 000 | 92 003 | 7 997 | 0 |

Rejets de la porte S :

| Porte | Entité | Règle | Lignes | Motif |
|---|---|---|---|---|
| S | client | RQ-007 | 430 | pays inconnu du référentiel après correspondance |
| S | client | RQ-009 | 14 | type de personne hors domaine et sans contrat |
| S | contrat | RQ-001 | 800 | date de fin absente ou <= date de début |
| S | contrat | RQ-010 | 600 | durée de garantie hors {12, 24, 36, 60} |
| S | sinistre | RQ-014 | 7 997 | adresse de sinistre non rapprochée de la BAN |

## 2. Porte S (US-23)

La couverture détaillée règle/table/population figure dans `reports/S4_couverture.json`, les comparaisons et exclusions dans `reports/S4_correctifs_synthese.json`. Les règles bloquantes requises passent sur les populations Silver retenues ; **RQ-003 reste un avertissement : 6 010 / 50 293 échecs, soit 88,05 %**. Les 7 997 adresses exclues ne sont pas déclarées réparées.

Les rapports `S4_rejeu.json` et `S4_tests_matrice.json` attestent l’idempotence historique et les cas limites. La correction du 15/11 garantit la fermeture du verrou même après exception ; cette branche est testée sans reconstruire les données nominales déjà certifiées.

## 3. Fusion et survie (US-24/25)

Décisions validées **D-14/D-15**, et non plus « en attente » : auto ≥ 90 ; revue 75 ≤ score < 90 ; maintien séparé sous 75. Nature connue identique, naissance identique pour PP, absence de contradiction géographique, compatibilité de toutes les paires du groupe.

Mesures de la construction initiale corrigée : 19 065 paires auto, 432 en revue, 121 073 identités pour 139 556 fiches Silver. Sur 200 paires : 95 VP, 0 FP, 5 FN, précision 100 %, rappel 95 %. Ces mesures d’échantillon ne garantissent pas l’exactitude de toutes les identités.

Meunier : CRM `A-4471`, `H-9012`, `S-2208` et CIF `K471226` → **CLI-033864**. Survie : candidats valides seulement pour les contacts, fréquence puis complétude pour le nom, bloc adresse/CP/commune/pays cohérent ; sans candidat valide, NULL et revue. Priorité CRM en égalité provisoire, sans prétention de fraîcheur.

**Contre-exemple exécuté de la vraie fonction de survie** : `reports/AUDIT_survie_contre_exemple.json`. Trois fiches synthétiques comportent deux anciens téléphones valides identiques et un téléphone de référence différent : la majorité sélectionne l’ancien. C’est une limite démontrée sur fixture, pas une erreur métier prétendument confirmée sur une personne réelle. Un conflit réel de naissance est documenté pour `CLI-001276` (10/12/1950 contre 12/10/1950) dans `reports/S4_US25_revue_survie.json` ; la vraie date reste à confirmer humainement.

## 4. Gold et évolution du périmètre (US-27)

La première configuration a été refusée : `reports/S4_VALIDATION_DATA_OWNER.json` et `livrables/s4_data_owner.md`. La correction RQ-019 du 12/11 a ensuite consolidé 23 cas et isolé 377 CLI (396 identifiants), avec leurs dépendances ; cette réserve n’est pas masquée par le GO final.

| Table Gold finale | Lignes | Exclusions G depuis Silver |
|---|---:|---|
| client_unique | 120 673 | 377 CLI isolés ; 23 consolidations supplémentaires |
| xref_identifiants | 139 160 | 396 identifiants exclus |
| contrat_certifie | 95 822 | 2 778 contrats, dont 337 liés à RQ-019 |
| sinistre_certifie | 88 824 | 3 179 sinistres, dont 332 liés à RQ-019 |

Aucun orphelin dans le périmètre final. `gold.v_client_actif` publie **36 041 CLI actifs**, date du lot, définition CD-001 unique. Les **4 178 contrats** et **11 176 sinistres** non publiés au total depuis Bronze incluent les rejets S, contrairement aux exclusions G seules.

## 5. Trois traces (US-28)

| Donnée | Gold | Origine et transformation |
|---|---|---|
| Société Meunier | CLI-033864, SOCIETE MEUNIER SARL | Quatre identifiants CRM/CIF via xref, Silver et Bronze |
| CP à zéro initial | CLI-000069, 01500 | CRM A-10062 : Bronze 1500, Silver/Gold 01500 |
| Adresse sinistre | SIN0000008, BAN012063 | « Platanees » → « Platanes » via rapprochement BAN |

Toutes les lignes, identifiants Bronze/Silver et lot sont conservés dans `reports/S4_traces_corrigees.json`. Requête : `pipelines/S4_US28_tracabilite.sql`.

## 6. Vérifications et limites

- [x] Conservation sur les quatre populations, rejets tracés et idempotence historique.
- [x] Garde-fous de fusion et survie, évaluation et limites explicites.
- [x] Gold final sans orphelin et trois traces jusqu’aux sources.
- [x] Exception de construction : verrou et connexion nettoyés par test ciblé.

Aucune relance de construction S4 sur le lot certifié pendant cet audit. Les sorties historiques restent identifiées comme telles ; la correction de nettoyage est vérifiée séparément. Temps historique non mesuré ; aucune restauration pédagogique déclarée. La revue humaine des 23 consolidations et 377 CLI demeure une action métier de suivi, pas un défaut technique artificiellement déclaré résolu.

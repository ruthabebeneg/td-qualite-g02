# Texte à intégrer au PPTX — S5 Data engineer

Groupe g02 · Mesures exécutées le 12/11/2026 dans Docker · Lot `L-2026-10-01`.
Le PPTX demeure inchangé. Repérer les pages par leur titre ; les numéros ci-dessous correspondent au modèle actuellement présent. Les courbes, le catalogue et la signature restent aux rôles concernés.

## « Certifier, publier, gouverner » (page 34)

« La chaîne technique S5 est exécutée et ses protections sont éprouvées. Le lot réel reste NO_GO : quatre contrôles RQ-019 échouent et le Data Owner a refusé la configuration S4. Aucune publication réelle n’a été effectuée. »

## « Historique des mesures et courbes d’évolution » (page 35)

« L’historique du lot contient 155 entrées, soit 112 clés règle/couche/table distinctes après normalisation des préfixes S4_/S5_. Cette exécution ajoute 25 mesures sans effacer les précédentes : 7 réconciliations RQ-021, 7 contrôles RQ-022, 4 signatures RQ-019, RQ-016 et 6 contrôles RQ-023 gold. La matrice de 25 règles × 3 couches contient 65 couples mesurés et 10 cas hors périmètre de couche justifiés. Les autres résultats sont des mesures historiques S4 relues, pas des remesures S5. »

Le tableau suivant donne le **minimum des taux parmi les tables et populations mesurées** de chaque règle/couche, calculé à partir des effectifs, arrondi à trois décimales. Il ne s’agit ni d’une moyenne ni d’une mesure unique par règle. Les dénominateurs détaillés sont dans `reports/S5_export_steward.json`. `—` : justification après le tableau. Le tableau complet peut servir d’annexe ; conserver cinq lignes lisibles sur la page du modèle.

| Règle | Dimension | Bronze % | Silver % | Gold % |
|---|---|---:|---:|---:|
| RQ-001 | Cohérence | 99,200 | 100,000 | 100,000 |
| RQ-002 | Validité métier | 98,616 | 98,600 | 100,000 |
| RQ-003 | Complétude | 88,005 | 88,050 | 89,244 |
| RQ-004 | Validité format | 71,803 | 99,004 | 100,000 |
| RQ-005 | Validité format | 98,477 | 100,000 | 100,000 |
| RQ-006 | Exactitude | 97,765 | 99,288 | 99,415 |
| RQ-007 | Intégrité référentielle | 96,950 | 100,000 | 100,000 |
| RQ-008 | Validité format | 98,499 | 98,499 | 100,000 |
| RQ-009 | Validité domaine | 99,800 | 100,000 | 100,000 |
| RQ-010 | Validité domaine | 99,400 | 100,000 | 100,000 |
| RQ-011 | Intégrité référentielle | 99,800 | 99,798 | 100,000 |
| RQ-012 | Intégrité référentielle | 99,000 | 98,586 | 100,000 |
| RQ-013 | Intégrité référentielle | 99,500 | 99,052 | 100,000 |
| RQ-014 | Précision, cohérence | 87,900 | 100,000 | 100,000 |
| RQ-015 | Cohérence de statut | 97,714 | 100,000 | 100,000 |
| RQ-016 | Cohérence de statut | 98,086 | 97,646 | 96,797 |
| RQ-017 | Cohérence inter-tables | 98,898 | 98,301 | 100,000 |
| RQ-018 | Cohérence de définition | 100,000 | 100,000 | 100,000 |
| RQ-019 | Unicité | 80,534 | 80,453 | 99,840 |
| RQ-020 | Unicité | 100,000 | 100,000 | 100,000 |
| RQ-021 | Complétude, intégrité | 100,000 | — | — |
| RQ-022 | Traçabilité | 100,000 | — | — |
| RQ-023 | Traçabilité | — | 100,000 | 100,000 |
| RQ-024 | Complétude | — | 100,000 | — |
| RQ-025 | Intégrité | — | — | — |

« RQ-021/022 concernent l’ingestion en bronze ; RQ-023 concerne les liens silver/gold vers bronze ; RQ-024 mesure la conservation bronze = silver + rejets. RQ-025 s’évalue après publication CRM, qui n’a pas eu lieu pour le lot réel. Ces absences de taux ne valent pas 100 %. CIF ne porte pas de rôle : RQ-003/009/015/016 ne s’appliquent pas à ses fiches prises isolément. Le Steward doit qualifier les justifications. »

« La baisse RQ-017 entre bronze et silver s’observe sur des populations différentes : 1 102 échecs / 100 000, puis 1 563 / 92 003. Hypothèse à faire vérifier par le Steward : la quarantaine modifie les contrats/renouvellements disponibles pour le contrôle ; ce résultat historique S4 nécessite une lecture par population, puis le gold exclut les sinistres non certifiables (0 / 89 156). RQ-016 passe de 1 184 / 50 293 échecs en silver à 1 552 / 48 456 en gold : des souscripteurs historiques sans contrat certifié restent A_REVOIR plutôt que devenir artificiellement prospects. »

Courbes : à produire et commenter par le Data Steward (US-30), à partir de `reports/S5_export_steward.json`. Aucune courbe ni stabilité temporelle supplémentaire n’est revendiquée par ce chantier.

## « Certificat de qualité : GO ou NO_GO » (page 36)

| Élément | Texte exact |
|---|---|
| Numéro du certificat | `S5-5a80973d5b68f8f925954718af8` |
| Lot | `L-2026-10-01` |
| Décision | NO_GO calculé par requête SQL |
| Règles bloquantes testées / conformes | 58 périmètres règle/couche/table testés / 54 conformes, couvrant 18 règles bloquantes B/S/G |
| Écarts connus (avertissements) | 7 mesures sous seuil sur les trois couches, concernant 4 règles distinctes (RQ-003/004/006/016) ; voir détail du certificat |
| Empreinte du gold | `72b494efa2bbcca6b67642dc83c4375683b54cc13a914b8ee882e1ff129c7154` |
| Signataire (rôle) | Aucun signataire S5 ; aucune signature humaine fabriquée. Refus Owner S4 documenté par Ruth le 08/11/2026. |

« Requête exécutée : sql/S5_decision.sql, appelée par pipelines/s5_engineering.py. Les absences et populations vides bloquent le GO. Aucun périmètre bloquant attendu n’est absent dans l’état réel mesuré ; quatre périmètres RQ-019 échouent. Le GO suppose également une acceptation Owner liée aux empreintes, absente pour ce lot refusé, et une attestation technique de réexécution complète des contrôles liée au contenu/configuration actuels. Cette attestation est absente : les historiques S4 relus ne suffisent pas et ce blocage est distinct de la décision humaine. Couverture : reports/S5_couverture.json. »

| RQ-019 : population gold | Testées | Échecs | Conséquence |
|---|---:|---:|---|
| identites_PP | 117963 | 189 | Bloque GO ; revue sans fusion automatique |
| identites_PM | 4062 | 5 | Bloque GO ; revue sans fusion automatique |
| signature_nom_cp_naissance_tel | 104615 | 114 | Bloque GO ; revue sans fusion automatique |
| signature_nom_email | 92493 | 83 | Bloque GO ; revue sans fusion automatique |

« Ces populations se recouvrent : ne pas additionner leurs échecs pour compter des personnes. RQ-016 confirme 1 552 échecs / 48 456 souscripteurs historiques, soit 96,797 % de conformité pour un seuil de 98 %. »

« Épreuve NO_GO : dans une fixture isolée s5_test_, la date de fin du contrat est mise égale à sa date de début. La mesure RQ-001 exécutée confirme 1 échec / 1 contrat ; malgré une attestation technique et une approbation de fixture valides, la requête produit NO_GO pour ce seul blocage. La suppression d’une mesure ou une population nulle produit aussi NO_GO. Le GO positif du mécanisme concerne exclusivement une fixture synthétique ; il ne démontre aucun GO du lot nominal. Preuves : reports/S5_tests.json. »

## « Publication vers le CRM : refus, chargement, réconciliation » (page 37)

| Scénario | Message obtenu | Chargement ? | Preuve |
|---|---|---|---|
| Sans certificat | CERTIFICAT_ABSENT | Non, lot réel et fixture | S5_refus_nominal.json ; S5_tests.json |
| Certificat NO_GO | CERTIFICAT_NO_GO | Non, lot réel et fixture | S5_refus_nominal.json ; S5_tests.json |
| Gold modifié après émission | EMPREINTE_GOLD_DIFFERENTE | Non, fixture isolée | S5_tests.json : gold_modifie |
| Certificat GO, gold intact | CHARGEE | Oui, fixture synthétique seulement | S5_tests.json : go_gold_intact |

Réconciliation RQ-025 **synthétique** : une ligne par table, pas de chargement nominal. Les SHA-256 complets ci-dessous peuvent être renvoyés en annexe pour préserver la lisibilité.

| Table | Lignes gold | Lignes CRM cible | SHA-256 gold | SHA-256 cible | Écart |
|---|---:|---:|---|---|---:|
| client | 1 | 1 | `5b259f72758944021866ba501962182d74512e5cb8055354c9886c0ac6bc3098` | `5b259f72758944021866ba501962182d74512e5cb8055354c9886c0ac6bc3098` | 0 |
| contrat | 1 | 1 | `f0390b36fb508a280e91a6abfefffaef59e746da5e4feb823358eb41c3a487a4` | `f0390b36fb508a280e91a6abfefffaef59e746da5e4feb823358eb41c3a487a4` | 0 |
| sinistre | 1 | 1 | `48a19602e3d410bd6a15870131bb74c7f8602a83c590937c994dda9f0f58f903` | `48a19602e3d410bd6a15870131bb74c7f8602a83c590937c994dda9f0f58f903` | 0 |

« Tout-ou-rien vérifié en injectant une panne après la copie de contrat, avec une cible préexistante non vide : les trois empreintes reviennent à leur valeur initiale après rollback. Les 35 tests d’intégration passent ; le rejeu ne crée aucun doublon. Script : pipelines/s5_engineering.py, fonction publish, appelée depuis notebooks/S5_g02.ipynb. La réconciliation est vérifiée avant commit. Un journal et les trois mesures CRM RQ-025 sont écrits dans cette même transaction ; une panne du journal démontre leur rollback. Les lignes cibles d’un autre lot et les moteurs MyISAM sont refusés avant écriture. »

« Les trois tables nominales crm_cible ont été préparées par création additive ; elles contiennent toujours zéro ligne. Les 24 tables sources/bronze/silver/gold (1 569 911 lignes au total, couches cumulées) ont des empreintes identiques avant/après. Preuves : reports/S5_immutabilite.json et reports/S5_refus_nominal.json. »

## « Gouvernance : catalogue, propriétaires, lineage » (page 38)

Cette page relève du Data Steward (US-34) : ne pas déclarer sa fiche réalisée. Références techniques transmises : `reports/S5_export_steward.json`, `reports/S4_sources_lineage.json`, `reports/S4_couverture.json`, tables `gold.xref_identifiants` et `silver.client`. Le Steward complète propriétaires, définition et règles à partir de ces preuves.

## « Bilan de S5 : critères de fin et difficultés » (page 39)

« [ ] Lot dégradé NO_GO et lot nominal GO : le NO_GO synthétique est démontré ; le lot nominal reste NO_GO. »
« [x] Refus sans certificat, avec NO_GO et après modification du gold : démontrés, modification sur fixture uniquement. »
« [ ] Réconciliation nominale après chargement : non démontrée car publication réelle interdite. Preuve technique synthétique disponible : trois tables, comptages et SHA-256 identiques ; elle ne clôt pas cet attendu nominal. »
« [ ] Décisions humaines et rendu global : à vérifier par les rôles concernés ; aucun nouveau seuil ou signature S5 créé par ce chantier. »

« Point de reprise pédagogique : non, aucune restauration de données utilisée. Incident d’outillage distinct : reprise de brouillons après interruption serveur ; fichiers regroupés dans le dépôt habituel, branche feat/s5-data-engineer ; exécution dans /tmp/s5_engineer_run du conteneur. Aucune reconstruction S4 ni relance du chargeur. Temps perdu humain : non mesuré, à renseigner par le groupe. »

« Amélioration proposée : conserver dès le départ la séparation entre l’implémentation des garde-fous et l’autorisation de migration réelle. Airflow US-33 non retenue ; courbes US-30, fiche US-34 et assemblage US-35 restent aux autres rôles. »

## Incohérences à signaler au rédacteur

- Le critère « lot nominal GO » du modèle est incompatible avec les échecs mesurés et le refus Owner S4 : le conserver non coché ; une fixture GO ne le remplace pas.
- Les 58 périmètres bloquants ne sont pas autant de règles : ils couvrent 18 règles distinctes ; les quatre échecs sont quatre populations de RQ-019.
- La mention ancienne « décisions Owner en attente » du plan du 08/11 est dépassée : la configuration actuelle est REFUSEE ; aucune autorisation de publication.
- Le support de référence SQL calcule la décision depuis les seules mesures présentes ; cela peut ignorer une bloquante absente. Ici une liste attendue est jointe explicitement et les tests de mesure absente/population vide refusent GO.
- Les voies SQL/Python du support ne calculent pas la même empreinte et certaines colonnes du support diffèrent du schéma réel. Une seule sérialisation typée est utilisée ici pour certificat, copie et réconciliation ; ne pas comparer ses SHA aux anciens algorithmes S4.
- Le minimum des taux par règle n’est pas une moyenne de dimension. Les périmètres et dénominateurs diffèrent selon couche ; une baisse ne prouve pas à elle seule une corruption.
- La page 35 et la page 38 ne sont pas terminées par la réalisation Data engineer : courbes et catalogue restent au Steward. Le PPTX n’a pas été modifié ni contrôlé visuellement après intégration.
- Les gabarits Markdown et AVANCEMENT restent volontairement inchangés ; le contrôle du dépôt ne valide pas leur complétude métier.

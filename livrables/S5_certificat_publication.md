# S5 · Certifier, publier vers le CRM, gouverner

Groupe : [À COMPLÉTER]  ·  Date : [À COMPLÉTER]  ·  Rédacteur : [À COMPLÉTER]  ·  Étiquette : `seance-5`

Un constat = un chiffre mesuré (règle, couche) + la preuve qui le reproduit + ce que cela change. Voir `README.md`.

## 1. Historique des mesures (US-29, US-30)

Une ligne par règle mesurée ; laissez vide la couche où la règle ne s'applique pas, et dites pourquoi.

| Règle | Dimension | Taux bronze | Taux silver | Taux gold | Évolution (monte, stable, descend) | Explication |
|---|---|---|---|---|---|---|
| … | … | … | … | … | … | … |
| … | … | … | … | … | … | … |
| … | … | … | … | … | … | … |
| … | … | … | … | … | … | … |
| … | … | … | … | … | … | … |
| … | … | … | … | … | … | … |

Courbes (chemin des images) : [À COMPLÉTER]

Toute règle qui descend d'une couche à l'autre : cause (filtre mal posé, conversion, effet de la quarantaine) et preuve : [À COMPLÉTER]

## 2. Certificat de qualité (US-31)

| Élément | Valeur |
|---|---|
| Numéro du certificat | … |
| Lot | … |
| Décision (GO ou NO_GO) | … |
| Règles bloquantes testées | … |
| Règles bloquantes conformes | … |
| Écarts connus (avertissements) | … |
| Empreinte du gold | … |
| Signataire (rôle) | … |

Requête de décision (chemin) : [À COMPLÉTER]

Épreuve du NO_GO : lot volontairement dégradé (comment), décision obtenue, preuve : [À COMPLÉTER]

Règles bloquantes non mesurées par votre pipeline et donc non couvertes par le certificat : [À COMPLÉTER]

## 3. Publication vers le CRM (US-32)

Script (chemin) : [À COMPLÉTER]

| Scénario | Message obtenu | Chargement effectué ? | Preuve |
|---|---|---|---|
| Sans certificat | … | … | … |
| Certificat NO_GO | … | … | … |
| Gold modifié après émission du certificat | … | … | … |
| Certificat GO et gold intact | … | … | … |

Réconciliation après chargement (RQ-025) :

| Table | Lignes gold | Lignes CRM cible | Somme de contrôle gold | Somme de contrôle CRM cible | Écart |
|---|---|---|---|---|---|
| client | … | … | … | … | … |
| contrat | … | … | … | … | … |
| sinistre | … | … | … | … | … |

Le chargement est-il tout-ou-rien ? Comment l'avez-vous vérifié : [À COMPLÉTER]

## 3 bis. Gouvernance (US-34)

Fiche de catalogue de `gold.client_unique` (chemin) : [À COMPLÉTER]

| Élément | Valeur |
|---|---|
| Propriétaire (Data Owner) | … |
| Steward (Data Steward) | … |
| Définition de « client actif » rattachée à la fiche | … |
| Règles RQ rattachées à la table | … |

Lineage de `gold.client_unique` jusqu'aux sources (liste ou schéma) : [À COMPLÉTER]

## 4. Décisions de la séance

Reportez dans `JOURNAL_DECISIONS.md` chaque seuil, sévérité ou règle de survie arrêté, avec son rôle. Nombre de décisions ajoutées en S5 : [À COMPLÉTER]

## 5. Critères de fin

- [ ] Un lot volontairement dégradé produit un NO_GO, le lot nominal un GO.
- [ ] La publication refuse sans certificat, avec une décision NO_GO, et quand le gold a changé.
- [ ] Après un chargement réussi, comptage et somme de contrôle sont égaux entre gold et CRM cible.
- [ ] Chaque décision de seuil ou de sévérité est attribuée à un rôle.

## 6. Difficultés, écarts avec l'attendu, reprise

Difficultés rencontrées et temps perdu : [À COMPLÉTER]

Point de reprise utilisé (oui / non, lequel) : [À COMPLÉTER]

Ce que nous ferions autrement : [À COMPLÉTER]

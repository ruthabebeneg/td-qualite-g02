# S4 · PySpark : construire silver puis gold

Groupe : [À COMPLÉTER]  ·  Date : [À COMPLÉTER]  ·  Rédacteur : [À COMPLÉTER]  ·  Étiquette : `seance-4`

Un constat = un chiffre mesuré (règle, couche) + la preuve qui le reproduit + ce que cela change. Voir `README.md`.

## 1. Silver et quarantaine (US-21, US-22)

Scripts ou notebooks (chemins) : [À COMPLÉTER]

Traitements appliqués (pays, code postal, identité, autres), avec le nombre de lignes touchées par chacun :

| Traitement | Table | Lignes modifiées | Garde-fou (ce que le traitement ne doit pas faire) |
|---|---|---|---|
| … | … | … | … |
| … | … | … | … |
| … | … | … | … |

Invariant silver + rejets = bronze :

| Table | Lignes bronze | Lignes silver | Lignes rejetées | Écart |
|---|---|---|---|---|
| client (crm) | … | … | … | … |
| client (cif) | … | … | … | … |
| contrat | … | … | … | … |
| sinistre | … | … | … | … |

Rejets par règle (`dq.rejets`) :

| Règle | Table | Lignes rejetées | Raison métier |
|---|---|---|---|
| … | … | … | … |
| … | … | … | … |

Idempotence : le traitement relancé deux fois donne le même résultat (preuve) : [À COMPLÉTER]

## 2. Porte S : bronze contre silver (US-23)

| Règle | Sévérité | Taux bronze | Taux silver | Écart | Explication de l'écart |
|---|---|---|---|---|---|
| … | … | … | … | … | … |
| … | … | … | … | … | … |
| … | … | … | … | … | … |
| … | … | … | … | … | … |
| … | … | … | … | … | … |

Toute règle dont le taux baisse de bronze à silver doit être expliquée : [À COMPLÉTER]

Règles bloquantes de la porte S toutes conformes sur silver ? Sinon, lesquelles et pourquoi : [À COMPLÉTER]

## 3. Dédoublonnage et golden record (US-24, US-25)

| Paramètre | Valeur retenue | Justification |
|---|---|---|
| Normalisation appliquée avant comparaison | … | … |
| Clé(s) de blocage | … | … |
| Mesure de similarité | … | … |
| Seuil de fusion automatique | … | … |
| Seuil de la zone de revue | … | … |

| Mesure | Valeur |
|---|---|
| Groupes de doublons trouvés | … |
| Paires fusionnées automatiquement | … |
| Paires en zone de revue | … |
| Précision sur les 200 paires étiquetées | … |
| Rappel sur les 200 paires étiquetées | … |
| Identités distinctes obtenues | … |

Golden record de la Société Meunier :

| Identifiant source | Système | CLI attribué |
|---|---|---|
| … | … | … |
| … | … | … |
| … | … | … |
| … | … | … |

Règle de survie par attribut :

| Attribut | Source retenue | Règle (priorité, plus récent, non nul) | Cas où la règle se trompe |
|---|---|---|---|
| Nom | … | … | … |
| Adresse | … | … | … |
| Téléphone | … | … | … |
| Courriel | … | … | … |

Reportez les seuils et la règle de survie dans `JOURNAL_DECISIONS.md`, avec le rôle qui les a décidés.

## 4. Gold et client actif (US-27)

| Table gold | Lignes | Lignes écartées (porte G) | Règles responsables |
|---|---|---|---|
| client_unique | … | … | … |
| xref_identifiants | … | … | … |
| contrat_certifie | … | … | … |
| sinistre_certifie | … | … | … |

Orphelins dans gold (contrat sans client, sinistre sans contrat) : [À COMPLÉTER]

Client actif publié par la vue `v_client_actif` : [À COMPLÉTER]. Écart avec la définition de la fiche CD-001 : [À COMPLÉTER]

Effet de la quarantaine sur l'intégrité en aval (un client écarté laisse-t-il des contrats orphelins ?) : [À COMPLÉTER]

## 5. Traçabilité de trois données (US-28)

| Donnée | Valeur dans gold | Silver (identifiants de ligne) | Bronze (identifiants de ligne, lot) | Source (table, clé) |
|---|---|---|---|---|
| Société Meunier | … | … | … | … |
| Un code postal à zéro initial | … | … | … | … |
| Une adresse de sinistre | … | … | … | … |

Requête de traçabilité (chemin) : [À COMPLÉTER]

## 6. Critères de fin

- [ ] Pour chaque table, silver + rejets = bronze, sans suppression silencieuse.
- [ ] Relancer le traitement deux fois donne le même résultat.
- [ ] Les règles bloquantes de la porte S sont conformes sur silver.
- [ ] Le gold ne contient aucun orphelin ; le client actif est publié par une seule vue.
- [ ] Les trois traces remontent du gold à la source avec identifiants de ligne et de lot.

## 7. Difficultés, écarts avec l'attendu, reprise

Difficultés rencontrées et temps perdu : [À COMPLÉTER]

Point de reprise utilisé (oui / non, lequel, à quel moment) : [À COMPLÉTER]

Ce que nous ferions autrement : [À COMPLÉTER]

SET NAMES utf8mb4;   -- le client de l'entrypoint Docker n'est pas forcement en UTF-8 : sans cette ligne, les accents sont enregistres deux fois
-- initdb/02_dq_regles.sql : catalogue des 25 regles qualite (user story v2, section 5)
-- A executer apres 00_medallion.sql (cree dq.regle). Severites et seuils : propositions a valider par le Data Owner.
INSERT INTO dq.regle (rule_id, libelle, dimension, porte, severite, seuil_min) VALUES
  ('RQ-001', 'La date de fin d''un contrat est postérieure à sa date de début', 'Cohérence', 'S', 'BLOQUANTE', 100.00),
  ('RQ-002', 'Un souscripteur personne physique a 18 ans ou plus à la date de début du contrat (un assuré peut être mineur)', 'Validité métier', 'G', 'BLOQUANTE', 100.00),
  ('RQ-003', 'Le téléphone d''un souscripteur est renseigné (ni nul, ni vide, ni blanc)', 'Complétude', 'S', 'AVERTISSEMENT', 98.00),
  ('RQ-004', 'Pour une adresse en France, le téléphone respecte le format à 10 chiffres une fois normalisé (+33 et 0033 convertis en 0)', 'Validité format', 'S', 'AVERTISSEMENT', 98.00),
  ('RQ-005', 'Pour une adresse en France, le code postal compte exactement 5 chiffres', 'Validité format', 'S', 'AVERTISSEMENT', 98.00),
  ('RQ-006', 'Pour une adresse en France, le couple code postal / commune existe dans le référentiel postal (après restauration du zéro initial)', 'Exactitude', 'S', 'AVERTISSEMENT', 98.00),
  ('RQ-007', 'Le pays (code ISO à deux lettres) appartient à la liste de référence', 'Intégrité référentielle', 'S', 'BLOQUANTE', 100.00),
  ('RQ-008', 'L''adresse e-mail respecte un motif valide', 'Validité format', 'S', 'AVERTISSEMENT', 98.00),
  ('RQ-009', 'Le type de personne vaut prospect, souscripteur ou assure (minuscules, sans accent, comme dans la base)', 'Validité domaine', 'S', 'BLOQUANTE', 100.00),
  ('RQ-010', 'La durée de garantie vaut 12, 24, 36 ou 60 mois', 'Validité domaine', 'S', 'BLOQUANTE', 100.00),
  ('RQ-011', 'Le type de contrat existe dans type_contrat', 'Intégrité référentielle', 'G', 'BLOQUANTE', 100.00),
  ('RQ-012', 'Le souscripteur d''un contrat existe dans le client', 'Intégrité référentielle', 'G', 'BLOQUANTE', 100.00),
  ('RQ-013', 'L''assuré d''un contrat existe dans le client ; la valeur sentinelle 0 est remplacée par NULL avant contrôle', 'Intégrité référentielle', 'G', 'BLOQUANTE', 100.00),
  ('RQ-014', 'Adresse de sinistre : format valide, rapprochée du référentiel national (BAN), enregistrement bloqué si échec', 'Précision, cohérence', 'S', 'BLOQUANTE', 100.00),
  ('RQ-015', 'Un prospect n''a aucun contrat', 'Cohérence de statut', 'G', 'BLOQUANTE', 100.00),
  ('RQ-016', 'Un souscripteur a au moins un contrat', 'Cohérence de statut', 'G', 'AVERTISSEMENT', 98.00),
  ('RQ-017', 'La date de survenance d''un sinistre est comprise dans la période de garantie du contrat', 'Cohérence inter-tables', 'G', 'BLOQUANTE', 100.00),
  ('RQ-018', 'Client actif : contrat en cours ET cotisation à jour sur 3 mois (fiche CD-001), à la date de référence du lot, calculé de façon identique pour les trois directions', 'Cohérence de définition', 'G', 'BLOQUANTE', 100.00),
  ('RQ-019', 'Une personne n''a qu''un seul identifiant client unique (CLI)', 'Unicité', 'G', 'BLOQUANTE', 100.00),
  ('RQ-020', 'Les clés primaires sont uniques et jamais nulles', 'Unicité', 'S', 'BLOQUANTE', 100.00),
  ('RQ-021', 'Réconciliation source vers bronze : mêmes comptages et mêmes sommes de contrôle par table', 'Complétude, intégrité', 'B', 'BLOQUANTE', 100.00),
  ('RQ-022', 'Chaque ligne bronze porte lot, source, horodatage et empreinte de ligne', 'Traçabilité', 'B', 'BLOQUANTE', 100.00),
  ('RQ-023', 'Chaque ligne silver et gold référence sa ligne bronze d''origine', 'Traçabilité', 'S', 'BLOQUANTE', 100.00),
  ('RQ-024', 'Conservation : lignes silver + lignes rejetées = lignes bronze', 'Complétude', 'S', 'BLOQUANTE', 100.00),
  ('RQ-025', 'Réconciliation gold vers CRM : même comptage et même somme de contrôle après chargement, rien de non certifié', 'Intégrité', 'C', 'BLOQUANTE', 100.00)
ON DUPLICATE KEY UPDATE libelle = VALUES(libelle), dimension = VALUES(dimension), porte = VALUES(porte), severite = VALUES(severite), seuil_min = VALUES(seuil_min);

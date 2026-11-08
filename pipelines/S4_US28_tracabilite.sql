-- S4 · US-28 : retracer trois données du gold jusqu'à la source (RQ-023)
-- Chaque trace : gold -> gold.xref_identifiants -> silver (silver_row_id) -> bronze (bronze_row_id, _batch_id) -> table source.
-- Lot visé : modifier @lot si besoin.
SET @lot := 'L-2026-10-01';

-- TRACE 1 : la Société Meunier SARL (CLI qui contient A-4471)
SET @cli := (SELECT cli_id FROM gold.xref_identifiants WHERE source_systeme = 'crm' AND source_id = 'A-4471' AND cli_id IN (SELECT cli_id FROM gold.client_unique WHERE _batch_id = @lot));

SELECT u.cli_id, u.nom_reference AS valeur_gold, x.source_systeme, x.source_id,
       s.silver_row_id, s.identite_normalisee AS valeur_silver, x.bronze_row_id,
       COALESCE(bc.raison_sociale, bf.column1) AS valeur_bronze, COALESCE(bc._batch_id, bf._batch_id) AS lot,
       CONCAT(x.source_systeme, IF(x.source_systeme = 'crm', '.client.client_id = ', '.clients.column0 = '), x.source_id) AS source,
       COALESCE(sc.raison_sociale, sf.column1) AS valeur_source
FROM gold.client_unique u
JOIN gold.xref_identifiants x ON x.cli_id = u.cli_id
JOIN silver.client s ON s.silver_row_id = x.silver_row_id
LEFT JOIN bronze.crm_client  bc ON x.source_systeme = 'crm' AND bc.bronze_row_id = x.bronze_row_id
LEFT JOIN bronze.cif_clients bf ON x.source_systeme = 'cif' AND bf.bronze_row_id = x.bronze_row_id
LEFT JOIN crm.client  sc ON x.source_systeme = 'crm' AND sc.client_id = x.source_id
LEFT JOIN cif.clients sf ON x.source_systeme = 'cif' AND sf.column0 = x.source_id
WHERE u.cli_id = @cli AND u._batch_id = @lot AND s._batch_id = @lot AND COALESCE(bc._batch_id, bf._batch_id) = @lot
ORDER BY x.source_systeme DESC, x.source_id;

-- TRACE 2 : un code postal à zéro initial restauré (bronze '1000' pour un client français -> silver/gold '01000')
SET @src := (SELECT b.client_id FROM bronze.crm_client b
             JOIN silver.client s ON s.source_systeme = 'crm' AND s.bronze_row_id = b.bronze_row_id
             JOIN gold.xref_identifiants x ON x.silver_row_id = s.silver_row_id
             WHERE b._batch_id = @lot AND b.cp REGEXP '^[0-9]{4}$' AND s.pays_iso = 'FR'
             ORDER BY b.client_id LIMIT 1);

SELECT u.cli_id, u.cp AS cp_gold, x.source_id, s.silver_row_id, s.cp AS cp_silver,
       x.bronze_row_id, b.cp AS cp_bronze, b.pays AS pays_bronze, b._batch_id AS lot, 'crm.client' AS source, c.cp AS cp_source
FROM gold.xref_identifiants x
JOIN gold.client_unique u ON u.cli_id = x.cli_id
JOIN silver.client s ON s.silver_row_id = x.silver_row_id
JOIN bronze.crm_client b ON b.bronze_row_id = x.bronze_row_id
JOIN crm.client c ON c.client_id = x.source_id
WHERE x.source_systeme = 'crm' AND x.source_id = @src AND u._batch_id = @lot AND s._batch_id = @lot AND b._batch_id = @lot;

-- TRACE 3 : une adresse de sinistre corrigée par la BAN (US-26)
SET @sin := (SELECT g.sinistre_id FROM gold.sinistre_certifie g JOIN silver.sinistre s ON s.silver_row_id = g.silver_row_id
             WHERE g._batch_id = @lot AND s.rapprochement_ban = 'CORRIGE' ORDER BY g.sinistre_id LIMIT 1);

SELECT g.sinistre_id, g.adresse_sinistre AS adresse_gold, g.id_ban, s.silver_row_id, s.adresse_sinistre AS adresse_silver, s.rapprochement_ban,
       g.bronze_row_id, b.adresse_sinistre AS adresse_bronze, b._batch_id AS lot,
       'crm.sinistre' AS source, c.adresse_sinistre AS adresse_source, g.contrat_id
FROM gold.sinistre_certifie g
JOIN silver.sinistre s ON s.silver_row_id = g.silver_row_id
JOIN bronze.crm_sinistre b ON b.bronze_row_id = g.bronze_row_id
JOIN crm.sinistre c ON c.sinistre_id = g.sinistre_id
WHERE g.sinistre_id = @sin AND g._batch_id = @lot AND s._batch_id = @lot AND b._batch_id = @lot;

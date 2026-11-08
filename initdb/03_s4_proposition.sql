-- S4 : migration additive, appliquée explicitement par S4_g02.ipynb.
-- Retour arrière manuel après archivage : DROP des colonnes ajoutées / table manifeste ;
-- ramener A_REVOIR vers un statut métier seulement après décision Owner, puis restaurer ENUM.
ALTER TABLE silver.client ADD COLUMN IF NOT EXISTS nature_personne VARCHAR(10) NULL;
ALTER TABLE gold.client_unique ADD COLUMN IF NOT EXISTS nature_personne VARCHAR(10) NULL;
ALTER TABLE gold.client_unique ADD COLUMN IF NOT EXISTS motif_revue VARCHAR(255) NULL;
ALTER TABLE gold.client_unique MODIFY COLUMN statut_client ENUM('PROSPECT','ASSURE','ACTIF','INACTIF','A_REVOIR') NOT NULL;
CREATE TABLE IF NOT EXISTS dq.s4_manifeste (
 batch_id VARCHAR(20) PRIMARY KEY, configuration_sha256 CHAR(64) NOT NULL,
 etat VARCHAR(40) NOT NULL, accepte BOOLEAN NOT NULL DEFAULT FALSE,
 modifie_le DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

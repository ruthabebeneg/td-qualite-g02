SET NAMES utf8mb4;   -- le client de l'entrypoint Docker n'est pas forcement en UTF-8 : sans cette ligne, les accents sont enregistres deux fois
-- initdb/00_medallion.sql  (exécuté une seule fois, au premier démarrage d'un volume vide)
-- Collation utf8mb4_nopad_bin : comparaison exacte (espaces de fin, casse et accents sont significatifs). Avec la collation par défaut de MariaDB, 'FR ' est égal à 'FR'
-- et masque une partie des anomalies de saisie que les règles doivent trouver (même résultat que pandas et DuckDB).
-- Bases cif, crm, bronze, silver, gold, dq, crm_cible ; mémoire de la qualité (dq) ; tables bronze, silver.client, gold.client_unique et xref.
CREATE DATABASE IF NOT EXISTS cif       CHARACTER SET utf8mb4 COLLATE utf8mb4_nopad_bin;
CREATE DATABASE IF NOT EXISTS crm       CHARACTER SET utf8mb4 COLLATE utf8mb4_nopad_bin;
CREATE DATABASE IF NOT EXISTS bronze    CHARACTER SET utf8mb4 COLLATE utf8mb4_nopad_bin;
CREATE DATABASE IF NOT EXISTS silver    CHARACTER SET utf8mb4 COLLATE utf8mb4_nopad_bin;
CREATE DATABASE IF NOT EXISTS gold      CHARACTER SET utf8mb4 COLLATE utf8mb4_nopad_bin;
CREATE DATABASE IF NOT EXISTS dq        CHARACTER SET utf8mb4 COLLATE utf8mb4_nopad_bin;
CREATE DATABASE IF NOT EXISTS crm_cible CHARACTER SET utf8mb4 COLLATE utf8mb4_nopad_bin;

-- Compte en lecture seule sur les sources (dev uniquement)
CREATE USER IF NOT EXISTS 'reader'@'%' IDENTIFIED BY 'reader';
GRANT SELECT ON cif.* TO 'reader'@'%';
GRANT SELECT ON crm.* TO 'reader'@'%';

-- ---------- dq : la mémoire de la qualité ----------
CREATE TABLE IF NOT EXISTS dq.lot_ingestion (
  batch_id    VARCHAR(20) PRIMARY KEY,                -- ex. L-2026-10-01
  started_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at DATETIME NULL,
  statut      ENUM('EN_COURS','TERMINE','ECHEC') NOT NULL DEFAULT 'EN_COURS'
);

CREATE TABLE IF NOT EXISTS dq.regle (
  rule_id    VARCHAR(10) PRIMARY KEY,                 -- RQ-001
  libelle    VARCHAR(255) NOT NULL,
  dimension  VARCHAR(40)  NOT NULL,
  porte      ENUM('B','S','G','C') NOT NULL,
  severite   ENUM('BLOQUANTE','AVERTISSEMENT') NOT NULL,
  seuil_min  DECIMAL(5,2) NOT NULL DEFAULT 100.00     -- taux de conformité minimal, en %
);

CREATE TABLE IF NOT EXISTS dq.dq_history (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  batch_id        VARCHAR(20) NOT NULL,
  couche          ENUM('BRONZE','SILVER','GOLD','CRM') NOT NULL,
  rule_id         VARCHAR(10) NOT NULL,
  table_cible     VARCHAR(60) NOT NULL,
  nb_testees      BIGINT NOT NULL,
  nb_echecs       BIGINT NOT NULL,
  taux_conformite DECIMAL(6,3) AS (100 * (nb_testees - nb_echecs) / NULLIF(nb_testees, 0)) STORED,
  mesure_le       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_lot_regle (batch_id, rule_id),
  FOREIGN KEY (rule_id) REFERENCES dq.regle (rule_id)
);

CREATE TABLE IF NOT EXISTS dq.rejets (
  id            BIGINT AUTO_INCREMENT PRIMARY KEY,
  batch_id      VARCHAR(20) NOT NULL,
  entite        VARCHAR(40) NOT NULL,                 -- client, contrat, sinistre
  source_systeme VARCHAR(20) NOT NULL DEFAULT 'crm',  -- crm ou cif : bronze_row_id n'est unique que par table bronze
  bronze_row_id BIGINT NOT NULL,
  rule_id       VARCHAR(10) NOT NULL,
  porte         ENUM('S','G') NOT NULL,
  motif         VARCHAR(255) NULL,
  rejete_le     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_lot_entite (batch_id, entite)
);

CREATE TABLE IF NOT EXISTS dq.certificat_qualite (
  certificat_id VARCHAR(30) PRIMARY KEY,              -- ex. CERT-L-2026-10-01
  batch_id      VARCHAR(20) NOT NULL,
  emis_le       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  nb_bloquantes_testees INT NOT NULL,
  nb_bloquantes_ok      INT NOT NULL,
  empreinte_gold CHAR(64) NOT NULL,                   -- SHA-256 des tables gold
  decision      ENUM('GO','NO_GO') NOT NULL,
  signataire    VARCHAR(80) NULL,
  commentaire   VARCHAR(500) NULL
);

-- Dernière mesure par lot, couche, règle et table
CREATE OR REPLACE VIEW dq.v_derniere_mesure AS
SELECT * FROM (
  SELECT h.*, ROW_NUMBER() OVER (PARTITION BY batch_id, couche, rule_id, table_cible ORDER BY id DESC) AS rn
  FROM dq.dq_history h
) t WHERE rn = 1;

CREATE OR REPLACE VIEW dq.dq_kpi AS
SELECT batch_id, couche, ROUND(AVG(taux_conformite), 2) AS taux_moyen,
       SUM(nb_echecs) AS total_echecs, MAX(mesure_le) AS derniere_mesure
FROM dq.dq_history GROUP BY batch_id, couche;

-- Même lecture par dimension de qualité du catalogue de règles (à rapprocher des 7 dimensions du CM2)
CREATE OR REPLACE VIEW dq.dq_kpi_dimension AS
SELECT m.batch_id, m.couche, r.dimension, ROUND(AVG(m.taux_conformite), 2) AS taux_moyen
FROM dq.v_derniere_mesure m JOIN dq.regle r USING (rule_id)
GROUP BY m.batch_id, m.couche, r.dimension;

-- ---------- bronze : copie fidèle + métadonnées d'ingestion (types texte) ----------
CREATE TABLE IF NOT EXISTS bronze.crm_client (
  bronze_row_id  BIGINT AUTO_INCREMENT PRIMARY KEY,
  client_id VARCHAR(12), type_personne VARCHAR(30), nom VARCHAR(150), prenom VARCHAR(80), raison_sociale VARCHAR(150),
  date_naissance VARCHAR(20), adresse VARCHAR(255), cp VARCHAR(10), ville VARCHAR(100),
  pays VARCHAR(40), telephone VARCHAR(30), email VARCHAR(150), date_creation VARCHAR(20),
  _batch_id      VARCHAR(20) NOT NULL,
  _source_system VARCHAR(20) NOT NULL DEFAULT 'crm',
  _ingested_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  _row_hash      CHAR(16) NOT NULL,
  KEY idx_batch (_batch_id), KEY idx_client (client_id)
) ENGINE=InnoDB;
-- ---------- bronze : les six autres tables, mêmes colonnes que la source (texte) + les quatre métadonnées ----------
CREATE TABLE IF NOT EXISTS bronze.cif_clients (
  bronze_row_id  BIGINT AUTO_INCREMENT PRIMARY KEY,
  column0 VARCHAR(255),
  column1 VARCHAR(255),
  column2 VARCHAR(255),
  column3 VARCHAR(255),
  column4 VARCHAR(255),
  column5 VARCHAR(255),
  column6 VARCHAR(255),
  column7 VARCHAR(255),
  column8 VARCHAR(255),
  column9 VARCHAR(255),
  _batch_id      VARCHAR(20) NOT NULL,
  _source_system VARCHAR(20) NOT NULL DEFAULT 'cif',
  _ingested_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  _row_hash      CHAR(16) NOT NULL,
  KEY idx_batch (_batch_id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS bronze.cif_compte (
  bronze_row_id  BIGINT AUTO_INCREMENT PRIMARY KEY,
  column0 VARCHAR(255),
  column1 VARCHAR(255),
  column2 VARCHAR(255),
  column3 VARCHAR(255),
  _batch_id      VARCHAR(20) NOT NULL,
  _source_system VARCHAR(20) NOT NULL DEFAULT 'cif',
  _ingested_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  _row_hash      CHAR(16) NOT NULL,
  KEY idx_batch (_batch_id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS bronze.cif_pays (
  bronze_row_id  BIGINT AUTO_INCREMENT PRIMARY KEY,
  code_pays VARCHAR(255),
  nom_pays VARCHAR(255),
  _batch_id      VARCHAR(20) NOT NULL,
  _source_system VARCHAR(20) NOT NULL DEFAULT 'cif',
  _ingested_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  _row_hash      CHAR(16) NOT NULL,
  KEY idx_batch (_batch_id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS bronze.crm_contrat (
  bronze_row_id  BIGINT AUTO_INCREMENT PRIMARY KEY,
  contrat_id VARCHAR(255),
  souscripteur_id VARCHAR(255),
  assure_id VARCHAR(255),
  code_type VARCHAR(255),
  date_debut VARCHAR(255),
  date_fin VARCHAR(255),
  duree_garantie_mois VARCHAR(255),
  prime_annuelle VARCHAR(255),
  date_derniere_cotisation VARCHAR(255),
  _batch_id      VARCHAR(20) NOT NULL,
  _source_system VARCHAR(20) NOT NULL DEFAULT 'crm',
  _ingested_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  _row_hash      CHAR(16) NOT NULL,
  KEY idx_batch (_batch_id), KEY idx_contrat (contrat_id), KEY idx_souscripteur (souscripteur_id), KEY idx_assure (assure_id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS bronze.crm_type_contrat (
  bronze_row_id  BIGINT AUTO_INCREMENT PRIMARY KEY,
  code_type VARCHAR(255),
  libelle VARCHAR(255),
  branche VARCHAR(255),
  _batch_id      VARCHAR(20) NOT NULL,
  _source_system VARCHAR(20) NOT NULL DEFAULT 'crm',
  _ingested_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  _row_hash      CHAR(16) NOT NULL,
  KEY idx_batch (_batch_id), KEY idx_type (code_type)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS bronze.crm_sinistre (
  bronze_row_id  BIGINT AUTO_INCREMENT PRIMARY KEY,
  sinistre_id VARCHAR(255),
  contrat_id VARCHAR(255),
  date_survenance VARCHAR(255),
  date_declaration VARCHAR(255),
  type_sinistre VARCHAR(255),
  montant_estime VARCHAR(255),
  adresse_sinistre VARCHAR(255),
  cp_sinistre VARCHAR(255),
  ville_sinistre VARCHAR(255),
  canal_saisie VARCHAR(255),
  _batch_id      VARCHAR(20) NOT NULL,
  _source_system VARCHAR(20) NOT NULL DEFAULT 'crm',
  _ingested_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  _row_hash      CHAR(16) NOT NULL,
  KEY idx_batch (_batch_id), KEY idx_contrat (contrat_id)
) ENGINE=InnoDB;


-- ---------- silver : standardisé, une ligne par ligne bronze conservée ----------
CREATE TABLE IF NOT EXISTS silver.client (
  silver_row_id  BIGINT AUTO_INCREMENT PRIMARY KEY,
  bronze_row_id  BIGINT NOT NULL,
  source_systeme VARCHAR(20) NOT NULL,
  source_id      VARCHAR(20) NOT NULL,
  type_personne  ENUM('prospect','souscripteur','assure') NULL,
  identite_normalisee VARCHAR(150), prenom_normalise VARCHAR(80), date_naissance DATE NULL,
  adresse_normalisee VARCHAR(255), cp VARCHAR(10), ville_normalisee VARCHAR(100), pays_iso CHAR(2),   -- cp : 'SW1A 1AA' ou '1000-001' pour l'étranger
  telephone_normalise VARCHAR(20), email_normalise VARCHAR(150),     -- un numéro irrécupérable est conservé tel quel : c'est RQ-004 qui le signale
  statut_qualite ENUM('VALIDE','A_SURVEILLER') NOT NULL DEFAULT 'VALIDE',
  _batch_id      VARCHAR(20) NOT NULL,
  _processed_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_bronze (source_systeme, bronze_row_id),  -- bronze_row_id n'est unique que dans sa table bronze
  KEY idx_source (source_systeme, source_id)
) ENGINE=InnoDB;

-- ---------- gold : consolidé, relié à silver et bronze ----------
CREATE TABLE IF NOT EXISTS gold.client_unique (
  cli_id         CHAR(10) PRIMARY KEY,                -- CLI-000482
  nom_reference  VARCHAR(150) NOT NULL,
  date_naissance DATE NULL,
  cp VARCHAR(10), ville VARCHAR(100), pays_iso CHAR(2),
  telephone VARCHAR(20), email VARCHAR(150),
  nb_identifiants_source INT NOT NULL,
  statut_client  ENUM('PROSPECT','ASSURE','ACTIF','INACTIF') NOT NULL,   -- ASSURE : couvert par un contrat dont il n'est pas le souscripteur
  _batch_id      VARCHAR(20) NOT NULL,
  KEY idx_identite (nom_reference, cp)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS gold.xref_identifiants (
  cli_id         CHAR(10) NOT NULL,
  source_systeme VARCHAR(20) NOT NULL,
  source_id      VARCHAR(20) NOT NULL,
  bronze_row_id  BIGINT NOT NULL,
  silver_row_id  BIGINT NOT NULL,
  PRIMARY KEY (source_systeme, source_id),
  FOREIGN KEY (cli_id) REFERENCES gold.client_unique (cli_id)
) ENGINE=InnoDB;

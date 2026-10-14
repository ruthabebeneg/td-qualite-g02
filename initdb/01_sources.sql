SET NAMES utf8mb4;   -- le client de l'entrypoint Docker n'est pas forcement en UTF-8 : sans cette ligne, les accents sont enregistres deux fois
-- initdb/01_sources.sql : tables des sources cif et crm, et referentiels (silver.ref_*)
-- A executer apres 00_medallion.sql (qui cree les bases). Les donnees sont chargees ensuite par pipelines/load_sources.py.
-- Choix assume : AUCUNE cle etrangere n'est declaree dans crm (le CRM maison n'impose pas l'integrite referentielle,
-- c'est ce que les etudiants doivent mesurer). Les cles primaires sont declarees et reellement uniques dans les donnees fournies.

-- ====================== crm (CRM maison, 3 branches : A auto, H habitation, S sante) ======================
CREATE TABLE IF NOT EXISTS crm.type_contrat (
  code_type VARCHAR(10)  NOT NULL PRIMARY KEY,
  libelle   VARCHAR(80)  NOT NULL,
  branche   VARCHAR(20)  NOT NULL                      -- AUTO, HABITATION, SANTE
);

CREATE TABLE IF NOT EXISTS crm.client (
  client_id      VARCHAR(12)  NOT NULL PRIMARY KEY,    -- prefixe de branche + numero : A-4471, H-9012, S-2208
  type_personne  VARCHAR(20)  NULL,                    -- domaine attendu : prospect, souscripteur, assure
  nom            VARCHAR(80)  NULL,                    -- NULL pour une personne morale
  prenom         VARCHAR(80)  NULL,
  raison_sociale VARCHAR(120) NULL,                    -- renseignee pour une personne morale
  date_naissance DATE         NULL,                    -- NULL pour une personne morale
  adresse        VARCHAR(120) NULL,
  cp             VARCHAR(10)  NULL,                    -- texte : le zero initial peut avoir ete perdu (A01)
  ville          VARCHAR(80)  NULL,
  pays           VARCHAR(10)  NULL,                    -- code ISO a 2 lettres attendu (FR) ; saisies libres observees (A02)
  telephone      VARCHAR(25)  NULL,
  email          VARCHAR(120) NULL,
  date_creation  DATE         NULL
);

CREATE TABLE IF NOT EXISTS crm.contrat (
  contrat_id               VARCHAR(12)   NOT NULL PRIMARY KEY,
  souscripteur_id          VARCHAR(12)   NULL,         -- reference crm.client, non imposee
  assure_id                VARCHAR(12)   NULL,         -- reference crm.client ; '0' = valeur sentinelle (A11)
  code_type                VARCHAR(10)   NULL,         -- reference crm.type_contrat, non imposee
  date_debut               DATE          NULL,
  date_fin                 DATE          NULL,
  duree_garantie_mois      INT           NULL,         -- domaine attendu : 12, 24, 36, 60
  prime_annuelle           DECIMAL(10,2) NULL,
  date_derniere_cotisation DATE          NULL,         -- sert a la regle « cotisation a jour sur 3 mois » (CD-001)
  KEY idx_souscripteur (souscripteur_id),
  KEY idx_assure (assure_id)
);

CREATE TABLE IF NOT EXISTS crm.sinistre (
  sinistre_id      VARCHAR(12)   NOT NULL PRIMARY KEY,
  contrat_id       VARCHAR(12)   NULL,
  date_survenance  DATE          NULL,
  date_declaration DATE          NULL,
  type_sinistre    VARCHAR(40)   NULL,
  montant_estime   DECIMAL(12,2) NULL,
  adresse_sinistre VARCHAR(160)  NULL,                 -- numero + voie
  cp_sinistre      VARCHAR(10)   NULL,
  ville_sinistre   VARCHAR(80)   NULL,
  canal_saisie     VARCHAR(30)   NULL,                 -- ressaisie_manuelle, portail_assure, import_expert, appel_telephonique
  KEY idx_contrat (contrat_id)
);

-- ====================== cif (depot central d'identites ; colonnes volontairement anonymes) ======================
-- Solution a donner a l'enseignant : column0 id_cif, column1 nom ou raison sociale, column2 prenom, column3 date de naissance (JJ/MM/AAAA),
-- column4 adresse, column5 code postal, column6 ville, column7 code pays, column8 telephone, column9 e-mail.
CREATE TABLE IF NOT EXISTS cif.clients (
  column0 VARCHAR(10)  NOT NULL PRIMARY KEY,
  column1 VARCHAR(120) NULL,
  column2 VARCHAR(80)  NULL,
  column3 VARCHAR(10)  NULL,
  column4 VARCHAR(120) NULL,
  column5 VARCHAR(10)  NULL,
  column6 VARCHAR(80)  NULL,
  column7 VARCHAR(5)   NULL,
  column8 VARCHAR(25)  NULL,
  column9 VARCHAR(120) NULL
);
-- compte : column0 id_compte, column1 id_cif (reference cif.clients), column2 date d'ouverture, column3 statut (O ouvert, F ferme)
CREATE TABLE IF NOT EXISTS cif.compte (
  column0 VARCHAR(12) NOT NULL PRIMARY KEY,
  column1 VARCHAR(10) NULL,
  column2 DATE        NULL,
  column3 CHAR(1)     NULL,
  KEY idx_cif (column1)
);
CREATE TABLE IF NOT EXISTS cif.pays (
  code_pays CHAR(2)     NOT NULL PRIMARY KEY,
  nom_pays  VARCHAR(80) NOT NULL
);

-- ====================== referentiels (silver.ref_*) ======================
CREATE TABLE IF NOT EXISTS silver.ref_pays (
  code_pays CHAR(2)     NOT NULL PRIMARY KEY,
  nom_pays  VARCHAR(80) NOT NULL
);
CREATE TABLE IF NOT EXISTS silver.ref_postal (          -- extrait pedagogique (178 couples) ; plusieurs communes par CP, deux CP pour Beaumont
  code_postal CHAR(5)     NOT NULL,
  commune     VARCHAR(80) NOT NULL,
  PRIMARY KEY (code_postal, commune)
);
CREATE TABLE IF NOT EXISTS silver.ref_ban (             -- extrait fictif de la Base Adresse Nationale (22 856 adresses)
  id_ban      CHAR(9)     NOT NULL PRIMARY KEY,
  numero      SMALLINT    NOT NULL,
  voie        VARCHAR(80) NOT NULL,
  code_postal CHAR(5)     NOT NULL,
  commune     VARCHAR(80) NOT NULL,
  KEY idx_adresse (code_postal, commune, voie, numero)
);

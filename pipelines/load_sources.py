# -*- coding: utf-8 -*-
"""Chargement des jeux de donnees AssurConnect dans MariaDB (bases cif, crm et referentiels silver.ref_*).

Usage (depuis le conteneur Jupyter) :
    python pipelines/load_sources.py                       # charge tout
    python pipelines/load_sources.py --reset               # vide les tables avant chargement
    python pipelines/load_sources.py --url mysql+pymysql://root:root@mariadb:3306

Convention des CSV : UTF-8, separateur virgule, valeur NULL ecrite \\N, chaine vide = chaine vide (distinction utile pour RQ-003).
Les tables doivent exister (initdb/00_medallion.sql puis 01_sources.sql). Le script verifie les comptages a l'arrivee.
"""
import argparse, os, sys
import pandas as pd
from sqlalchemy import create_engine, text

ROOT = os.environ.get("ASSURCONNECT_DATA", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
# (fichier relatif, schema, table, colonnes de date)
CIBLES = [
    ("sources/crm/type_contrat.csv", "crm", "type_contrat", []),
    ("sources/crm/client.csv", "crm", "client", ["date_naissance", "date_creation"]),
    ("sources/crm/contrat.csv", "crm", "contrat", ["date_debut", "date_fin", "date_derniere_cotisation"]),
    ("sources/crm/sinistre.csv", "crm", "sinistre", ["date_survenance", "date_declaration"]),
    ("sources/cif/clients.csv", "cif", "clients", []),
    ("sources/cif/compte.csv", "cif", "compte", ["column2"]),
    ("sources/cif/pays.csv", "cif", "pays", []),
    ("referentiels/ref_pays.csv", "silver", "ref_pays", []),
    ("referentiels/ref_postal.csv", "silver", "ref_postal", []),
    ("referentiels/ref_ban.csv", "silver", "ref_ban", []),
]

def lire(chemin):
    # keep_default_na=False : seul \N est NULL ; '' et '   ' restent des valeurs (nul, vide et blanc sont trois cas)
    return pd.read_csv(chemin, dtype=str, keep_default_na=False, na_values=["\\N"], encoding="utf-8")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("DQ_DB_URL", "mysql+pymysql://root:root@mariadb:3306"))
    ap.add_argument("--reset", action="store_true", help="TRUNCATE des tables cibles avant chargement")
    ap.add_argument("--data", default=ROOT)
    a = ap.parse_args()
    eng = create_engine(a.url)
    ecarts = 0
    with eng.begin() as cx:
        for rel, schema, table, dates in CIBLES:
            df = lire(os.path.join(a.data, rel))
            for c in dates:                                   # dates ISO -> NULL si absente
                df[c] = df[c].where(df[c].notna(), None)
            if a.reset:
                cx.execute(text(f"DELETE FROM {schema}.{table}"))
            df = df.astype(object).where(df.notna(), None)
            df.to_sql(table, cx, schema=schema, if_exists="append", index=False, method="multi", chunksize=2000)
            n = cx.execute(text(f"SELECT COUNT(*) FROM {schema}.{table}")).scalar()
            ok = (n == len(df))
            ecarts += (not ok)
            print(f"{schema}.{table:<14} fichier {len(df):>7}  base {n:>7}  {'OK' if ok else 'ECART'}")
    print("Chargement termine, ecarts :", ecarts)
    sys.exit(1 if ecarts else 0)

if __name__ == "__main__":
    main()

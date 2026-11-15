"""Rejouer S1/S2/S5 sans modifier l'historique nominal déjà certifié.

À lancer dans le conteneur Jupyter avec les dépendances épinglées du projet.
Les écritures S2 utilisent un schéma unique détruit même en cas d'échec.
S4 n'est jamais reconstruit ; S5 vérifie le lot déjà publié sans rechargement.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

import nbformat
from nbclient import NotebookClient
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = (
    "US-09_client_actif", "S2_US10_regles_en_tests",
    "S2_US11_lignes_en_echec", "S2_g02", "S5_data_steward", "S5_g02",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date-comparaison", default=date.today().isoformat())
    parser.add_argument("--notebooks", nargs="+", choices=NOTEBOOKS, default=list(NOTEBOOKS))
    parser.add_argument("--silver", action="store_true", help="Rejouer uniquement GE sur Silver et préserver les sorties Bronze")
    args = parser.parse_args()
    if args.silver:
        args.notebooks = ["S2_US10_regles_en_tests"]
    date.fromisoformat(args.date_comparaison)
    schema = "s5_test_audit_" + uuid4().hex[:12]
    engine = create_engine(os.environ.get("DQ_DB_URL", "mysql+pymysql://root:root@mariadb:3306/dq"))
    variable_names = ("DQ_HISTORY_SCHEMA", "DQ_COMPARISON_DATE", "DQ_WRITE_DATABASE_URL", "DQ_SCHEMA", "DQ_S2_LAYER", "DQ_S2_EXECUTION_REPORT")
    previous = {name: os.environ.get(name) for name in variable_names}
    os.environ["DQ_HISTORY_SCHEMA"] = schema
    os.environ["DQ_COMPARISON_DATE"] = args.date_comparaison
    os.environ.setdefault("DQ_WRITE_DATABASE_URL", str(engine.url.render_as_string(hide_password=False)))
    os.environ["DQ_SCHEMA"] = "silver" if args.silver else "bronze"
    os.environ["DQ_S2_LAYER"] = "SILVER" if args.silver else "BRONZE"
    os.environ["DQ_S2_EXECUTION_REPORT"] = str(ROOT / "reports" / ("S2_execution_" + schema + ".json"))
    report = {
        "debut": datetime.now(timezone.utc).isoformat(),
        "schema_validation": schema,
        "couche": os.environ["DQ_S2_LAYER"],
        "schema_source": os.environ["DQ_SCHEMA"],
        "tables": {"client": os.getenv("DQ_TABLE_CLIENT", "client" if args.silver else "crm_client"),
                   "contrat": os.getenv("DQ_TABLE_CONTRAT", "contrat" if args.silver else "crm_contrat")},
        "rapport_mesures": os.environ["DQ_S2_EXECUTION_REPORT"],
        "date_comparaison": args.date_comparaison,
        "historique_nominal_modifie": False,
        "notebooks": [],
        "tous_passes": False,
    }
    created = False
    try:
        if "S5_g02" in args.notebooks:
            sys.path.insert(0, str(ROOT / "pipelines"))
            import audit_final
            certificate = json.loads((ROOT / "reports/S5_certificat_final.json").read_text())
            if audit_final.published_state(engine, certificate["batch_id"], certificate) is None:
                raise RuntimeError(
                    "Cette validation requiert un lot déjà publié : la première publication "
                    "et ses décisions métier constituent un parcours distinct."
                )
        with engine.begin() as cx:
            cx.execute(text(f"CREATE DATABASE `{schema}`"))
            created = True
            cx.execute(text(f"CREATE TABLE `{schema}`.dq_history LIKE dq.dq_history"))
        for name in args.notebooks:
            path = ROOT / "notebooks" / (name + ".ipynb")
            notebook = nbformat.read(path, as_version=4)
            print(f"Exécution de {name}", flush=True)
            NotebookClient(
                notebook, timeout=900, kernel_name="python3",
                resources={"metadata": {"path": str(ROOT / "notebooks")}},
            ).execute()
            # Seules les exécutions réussies remplacent les sorties livrées.
            if not args.silver:
                nbformat.write(notebook, path)
            report["notebooks"].append({
                "notebook": name, "resultat": "PASSE",
                "cellules_executees": sum(
                    c.cell_type == "code" and bool(c.source.strip()) for c in notebook.cells
                ),
            })
        report["tous_passes"] = True
    finally:
        try:
            if created:
                with engine.begin() as cx:
                    cx.execute(text(f"DROP DATABASE `{schema}`"))
            report["schema_nettoye"] = True
        finally:
            engine.dispose()
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
            report["fin"] = datetime.now(timezone.utc).isoformat()
            output = ROOT / "reports" / "executions" / ("notebooks_" + schema)
            output.mkdir(parents=True, exist_ok=True)
            (output / "validation.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            print(f"Rapport : {output.relative_to(ROOT) / 'validation.json'}", flush=True)


if __name__ == "__main__":
    main()

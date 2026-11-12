"""Outils S5 appelés depuis S5_g02.ipynb.

Les fonctions ne démarrent aucun traitement à l'import. Les écritures sont
limitées à dq (certificats) et crm_cible ; les scénarios synthétiques utilisent
exclusivement des schémas dont le nom commence par ``s5_test_``.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
import re
from uuid import uuid4
from pathlib import Path
from typing import Any

from sqlalchemy import text


class PublicationRefusee(RuntimeError):
    """Refus explicite, avant commit et sans chargement partiel."""


@dataclass(frozen=True)
class Layout:
    gold: str = "gold"
    dq: str = "dq"
    target: str = "crm_cible"

    def __post_init__(self):
        for value in (self.gold, self.dq, self.target):
            ident(value)
        if (self.gold, self.dq, self.target) != ("gold", "dq", "crm_cible"):
            if not all(x.startswith("s5_test_") for x in
                       (self.gold, self.dq, self.target)):
                raise ValueError("Un environnement alternatif doit être isolé s5_test_.")

    @property
    def synthetic(self):
        return self.gold.startswith("s5_test_")


MAPPING = (("client_unique", "client"), ("contrat_certifie", "contrat"),
           ("sinistre_certifie", "sinistre"))
BRONZE_TABLES = ("crm_client", "crm_contrat", "crm_sinistre", "crm_type_contrat",
                "cif_clients", "cif_compte", "cif_pays")


def ident(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError("Identifiant SQL refusé")
    return f"`{value}`"


def table(schema, name):
    return f"{ident(schema)}.{ident(name)}"


def canonical(value: Any):
    """Sérialisation typée : NULL, vide, blanc, dates et décimales distincts."""
    if value is None:
        return ["null"]
    if isinstance(value, bool):
        return ["bool", value]
    if isinstance(value, int):
        return ["int", str(value)]
    if isinstance(value, Decimal):
        return ["decimal", format(value, "f")]
    if isinstance(value, (datetime, date)):
        return [type(value).__name__, value.isoformat()]
    if isinstance(value, bytes):
        return ["bytes", value.hex()]
    if isinstance(value, float):
        return ["float", value.hex()]
    if isinstance(value, str):
        return ["str", value]
    raise TypeError(f"Type non pris en charge : {type(value).__name__}")


def json_bytes(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), default=str).encode("utf-8")


def digest(value):
    return hashlib.sha256(json_bytes(value)).hexdigest()


def rows(cx, sql, params=None):
    return [dict(r) for r in cx.execute(text(sql), params or {}).mappings()]


def columns(cx, schema, name):
    return rows(cx, """SELECT COLUMN_NAME AS name, COLUMN_TYPE AS type,
        IS_NULLABLE AS nullable, COLUMN_KEY AS column_key
        FROM information_schema.columns WHERE table_schema=:s AND table_name=:t
        ORDER BY ORDINAL_POSITION""", {"s": schema, "t": name})


def table_pages(cx, schema, name, names, batch=None, batch_column="_batch_id", size=1000):
    """Pages bornées et déterministes sur le même snapshot, sans buffer global."""
    meta = columns(cx, schema, name)
    order = [m["name"] for m in meta if m["column_key"] == "PRI"] or [m["name"] for m in meta]
    fields = ",".join(ident(n) for n in names)
    where = f" WHERE {ident(batch_column)}=:batch" if batch is not None else ""
    sql = (f"SELECT {fields} FROM {table(schema,name)}{where} ORDER BY " +
           ",".join(ident(n) for n in order) + " LIMIT :size OFFSET :offset")
    offset = 0
    while True:
        page = cx.execution_options(stream_results=False).execute(text(sql),
            {"batch":batch,"size":size,"offset":offset}).mappings().all()
        if not page:
            return
        yield page
        offset += len(page)


def fingerprint_table(cx, schema, name, batch=None, batch_column="_batch_id"):
    """SHA256 par pages bornées ; types et ordre total explicités."""
    meta = columns(cx, schema, name)
    if not meta:
        raise ValueError(f"Table absente : {schema}.{name}")
    names = [m["name"] for m in meta]
    if batch is not None and batch_column not in names:
        raise ValueError(f"Colonne de lot absente : {schema}.{name}")
    h = hashlib.sha256()
    h.update(json_bytes([[m["name"],m["type"],m["nullable"]] for m in meta]))
    count = 0
    for page in table_pages(cx,schema,name,names,batch,batch_column):
        for row in page:
            payload = json_bytes([canonical(row[n]) for n in names])
            h.update(len(payload).to_bytes(8,"big")); h.update(payload)
            count += 1
    return {"lignes":count,"sha256":h.hexdigest(),"colonnes":names}


def fingerprint_gold(cx, batch, layout=Layout()):
    detail = {source: fingerprint_table(cx, layout.gold, source, batch)
              for source, _ in MAPPING}
    return {"batch_id": batch, "tables": detail, "sha256": digest(detail)}


@contextmanager
def coherent_connection(engine):
    """Même verrou que S4 et snapshot reproductible jusqu'à la fin.

    Les lectures et les copies Python utilisent le même snapshot InnoDB.
    Un écrivain extérieur ignorant GET_LOCK ne peut donc pas modifier le
    contenu effectivement copié après sa vérification.
    """
    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as cx:
        if cx.execute(text("SELECT GET_LOCK('s4_construction',0)")).scalar() != 1:
            cx.rollback()
            raise PublicationRefusee("CONSTRUCTION_CONCURRENTE")
        cx.commit()
        try:
            with cx.begin():
                yield cx
        finally:
            if cx.in_transaction():
                cx.rollback()
            cx.execute(text("SELECT RELEASE_LOCK('s4_construction')"))
            cx.commit()


def _history(cx, batch, layout):
    all_rows = rows(cx, f"""SELECT h.*,r.dimension,r.porte,r.severite,r.seuil_min
        FROM {table(layout.dq,'dq_history')} h
        JOIN {table(layout.dq,'regle')} r USING(rule_id)
        WHERE h.batch_id=:batch ORDER BY h.id""", {"batch": batch})
    latest = {}
    for r in all_rows:
        # Le préfixe S4_ est un espace de noms du notebook, pas une autre table.
        r["table_logique"] = r["table_cible"].removeprefix("S4R19_").removeprefix("S4_").removeprefix("S5_")
        latest[(r["couche"], r["rule_id"], r["table_logique"])] = r
    invalid = []
    for r in all_rows:
        n, e = r["nb_testees"], r["nb_echecs"]
        if n < 0 or e < 0 or e > n:
            invalid.append(r["id"])
    return {"batch_id": batch, "mesures": list(latest.values()),
            "lignes_historiques": len(all_rows), "mesures_courantes": len(latest),
            "doublons_historiques": len(all_rows)-len(latest),
            "mesures_invalides": [r["id"] for r in all_rows if r["id"] in invalid and r["couche"] != "CRM"],
            "sha256": digest([r for r in all_rows if r["couche"] in ("BRONZE","SILVER","GOLD")]),
            "perimetre_sha256": "Mesures B/S/G ; CRM RQ-025 exclu pour préserver le rejeu"}


def audit_history(engine, batch, layout=Layout()):
    """Lecture seule de l'historique ; les anciennes mesures sont préservées."""
    with coherent_connection(engine) as cx:
        return _history(cx, batch, layout)


def required_scopes(catalogue, *, synthetic=False):
    """Périmètre explicite par table : aucune règle n'est satisfaite par hasard."""
    base = {
        "RQ-001": ["contrat"], "RQ-002": ["contrat"],
        "RQ-007": ["client_crm", "client_cif"], "RQ-009": ["client_crm"],
        "RQ-010": ["contrat"], "RQ-011": ["contrat"],
        "RQ-012": ["contrat"], "RQ-013": ["contrat"],
        "RQ-014": ["sinistre"], "RQ-015": ["client_unique"],
        "RQ-017": ["sinistre_garantie", "sinistre_relation"],
        "RQ-018": ["v_client_actif", "statut_client_actif"],
        "RQ-019": ["identites_PP", "identites_PM",
                   "signature_nom_cp_naissance_tel", "signature_nom_email"],
        "RQ-020": ["client_crm", "client_cif", "contrat", "sinistre"],
        "RQ-021": list(BRONZE_TABLES), "RQ-022": list(BRONZE_TABLES),
        "RQ-023": ["client_crm", "client_cif", "contrat_crm", "sinistre_crm"],
        "RQ-024": ["client (crm)", "client (cif)", "contrat (crm)", "sinistre (crm)"],
    }
    output = []
    for r in catalogue:
        if r["severite"] != "BLOQUANTE" or r["porte"] == "C":
            continue
        layer = {"B": "BRONZE", "S": "SILVER", "G": "GOLD"}[r["porte"]]
        scopes = base.get(r["rule_id"], ["PERIMETRE_A_DEFINIR"])
        for name in scopes:
            output.append({"rule_id": r["rule_id"], "couche": layer,
                           "table_logique": name, "seuil_min": str(r["seuil_min"])})
    # RQ-023 porte aussi explicitement sur gold, indépendamment de sa porte S.
    rule = next((r for r in catalogue if r["rule_id"] == "RQ-023" and r["severite"] == "BLOQUANTE"), None)
    if rule:
        for name in ("xref_crm","xref_cif","contrat_certifie","sinistre_certifie",
                     "client_unique","silver_xref_gold"):
            output.append({"rule_id":"RQ-023","couche":"GOLD","table_logique":name,
                           "seuil_min":str(rule["seuil_min"])})
    return output


def init_storage(engine, layout=Layout()):
    """DDL additive explicite, hors transaction de publication."""
    with engine.begin() as cx:
        cx.execute(text(f"""CREATE TABLE IF NOT EXISTS {table(layout.dq,'s5_certification')} (
            certificat_id VARCHAR(30) PRIMARY KEY, batch_id VARCHAR(20) NOT NULL,
            preuve LONGTEXT NOT NULL, preuve_sha256 CHAR(64) NOT NULL,
            emis_le DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ) ENGINE=InnoDB"""))
        cx.execute(text(f"""CREATE TABLE IF NOT EXISTS {table(layout.dq,'s5_publication')} (
            publication_id CHAR(32) PRIMARY KEY, certificat_id VARCHAR(30) NOT NULL,
            batch_id VARCHAR(20) NOT NULL, empreinte_gold CHAR(64) NOT NULL,
            preuve LONGTEXT NOT NULL, publie_le DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ) ENGINE=InnoDB"""))


def prepare_target(engine, layout=Layout()):
    """Prépare les trois tables ; n'efface et ne charge aucune ligne."""
    with engine.begin() as cx:
        cx.execute(text(f"CREATE DATABASE IF NOT EXISTS {ident(layout.target)} CHARACTER SET utf8mb4 COLLATE utf8mb4_nopad_bin"))
        for source, target_name in MAPPING:
            cx.execute(text(f"CREATE TABLE IF NOT EXISTS {table(layout.target,target_name)} LIKE {table(layout.gold,source)}"))
            source_meta = columns(cx, layout.gold, source)
            target_meta = columns(cx, layout.target, target_name)
            if source_meta != target_meta:
                raise ValueError(f"Mapping incompatible : {source} → {target_name}")
            engine_type = cx.execute(text("SELECT ENGINE FROM information_schema.tables WHERE table_schema=:s AND table_name=:t"),
                                     {"s": layout.target, "t": target_name}).scalar()
            if engine_type != "InnoDB":
                raise ValueError("La cible doit être transactionnelle InnoDB")


def assert_transactional(cx, layout):
    """Vérifie à chaque appel tous les moteurs des lectures et écritures protégées."""
    schemas = {layout.gold,layout.dq,layout.target}
    if not layout.synthetic:
        schemas.update(("crm","cif","bronze","silver"))
    info = rows(cx,"SELECT table_schema,table_name,engine FROM information_schema.tables WHERE table_type='BASE TABLE'")
    for item in info:
        if item["table_schema"] in schemas and item["engine"] != "InnoDB":
            raise PublicationRefusee("MOTEUR_NON_TRANSACTIONNEL:"+item["table_schema"]+"."+item["table_name"]+":"+str(item["engine"]))
    needed = [(layout.gold,n) for n,_ in MAPPING] + [(layout.target,n) for _,n in MAPPING]
    needed += [(layout.dq,n) for n in ("regle","dq_history","certificat_qualite","s4_manifeste","s5_certification","s5_publication")]
    found={(i["table_schema"],i["table_name"]) for i in info}
    if any(pair not in found for pair in needed):
        raise PublicationRefusee("PREPARATION_TABLES_INCOMPLETE")


def policy_fingerprint(catalogue, layout):
    root=Path(__file__).resolve().parents[1]
    files=("sql/S5_decision.sql","pipelines/s5_engineering.py","pipelines/s5_mesures.py",
           "pipelines/s5_controles.py","pipelines/s4_rq019.py")
    return digest({"fichiers":{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files},
                   "scopes":required_scopes(catalogue,synthetic=layout.synthetic),
                   "mapping":[list(m) for m in MAPPING]})


def control_content(cx, layout):
    """Contenu des tables de contrôle, indépendant des écritures de certification."""
    schemas={layout.gold} if layout.synthetic else {"crm","cif","bronze","silver","gold"}
    tables=rows(cx,"SELECT table_schema,table_name FROM information_schema.tables WHERE table_type='BASE TABLE' ORDER BY table_schema,table_name")
    return digest({item["table_schema"]+"."+item["table_name"]:
                   fingerprint_table(cx,item["table_schema"],item["table_name"])
                   for item in tables if item["table_schema"] in schemas or
                   (item["table_schema"] == layout.dq and
                    (item["table_name"] in ("rejets","rq019_etat") or
                     item["table_name"].startswith("rq019_reference_")))})


def measure_fixture(engine, batch, layout):
    """Attestation technique limitée à la fixture RQ-001 réellement mesurée.

    Aucune fonction n'atteste automatiquement le lot nominal : la réexécution
    exhaustive des contrôles S1/S4 avec liens de contenu n'a pas été réalisée.
    """
    if not layout.synthetic:
        raise ValueError("Attestation automatique réservée aux fixtures techniques")
    with coherent_connection(engine) as cx:
        assert_transactional(cx,layout)
        catalogue=_catalogue(cx,layout)
        expected=required_scopes(catalogue,synthetic=True)
        if [(x["rule_id"],x["couche"],x["table_logique"]) for x in expected] != [("RQ-001","SILVER","contrat")]:
            raise ValueError("Cette fixture n'exécute que RQ-001")
        n,e=cx.execute(text(f"SELECT COUNT(*),COALESCE(SUM(date_fin IS NULL OR date_debut IS NULL OR date_fin<=date_debut),0) FROM {table(layout.gold,'contrat_certifie')} WHERE _batch_id=:b"),{"b":batch}).one()
        history=_history(cx,batch,layout)
        current=next((m for m in history["mesures"] if m["rule_id"]=="RQ-001" and m["couche"]=="SILVER" and m["table_logique"]=="contrat"),None)
        if not current or (current["nb_testees"],current["nb_echecs"]) != (n,e):
            raise ValueError("Mesure fixture différente de l'historique")
        return {"synthetique":True,"batch_id":batch,"schema_gold":layout.gold,"schema_dq":layout.dq,
                "gold_sha256":fingerprint_gold(cx,batch,layout)["sha256"],
                "history_sha256":history["sha256"],"configuration":_manifest(cx,batch,layout),
                "catalogue_sha256":digest(catalogue),"politique_sha256":policy_fingerprint(catalogue,layout),
                "contenu_controles_sha256":control_content(cx,layout),
                "scopes_sha256":digest(expected),"mesures_executees":[{"scope":expected[0],"nb_testees":int(n),"nb_echecs":int(e)}]}


def attestation_valid(cx, attestation, batch, layout, gold, history, catalogue, manifest):
    """Contrat d'intégration pour les preuves d'un exécuteur complet de contrôles.

    L’exécuteur s5_controles fournit les mesures nominales réellement recalculées
    et les empreintes du contenu contrôlé. Une lecture des seuls taux historiques
    ne constitue jamais une attestation valide.
    """
    if not isinstance(attestation,dict) or not attestation.get("contenu_controles_sha256"):
        return False
    expected=required_scopes(catalogue,synthetic=layout.synthetic)
    coverage=_coverage(history,catalogue,layout)
    known={(m["couche"],m["rule_id"],m["table_logique"]) for m in expected}
    for m in coverage:
        key=(m["couche"],m["rule_id"],m["table_logique"])
        if key not in known:
            r=next(r for r in catalogue if r["rule_id"]==m["rule_id"])
            expected.append({"rule_id":m["rule_id"],"couche":m["couche"],"table_logique":m["table_logique"],"seuil_min":str(r["seuil_min"])})
    executed=attestation.get("mesures_executees",[])
    current={(m["couche"],m["rule_id"],m["table_logique"]):m for m in history["mesures"]}
    if [m.get("scope") for m in executed] != expected:
        return False
    for result in executed:
        scope=result["scope"]
        m=current.get((scope["couche"],scope["rule_id"],scope["table_logique"]))
        if not m or (result.get("nb_testees"),result.get("nb_echecs")) != (m["nb_testees"],m["nb_echecs"]):
            return False
    bound=bool(attestation.get("synthetique") is layout.synthetic and attestation.get("batch_id")==batch
        and attestation.get("schema_gold")==layout.gold and attestation.get("schema_dq")==layout.dq
        and attestation.get("gold_sha256")==gold["sha256"]
        and attestation.get("history_sha256")==history["sha256"]
        and digest(attestation.get("configuration"))==digest(manifest)
        and attestation.get("catalogue_sha256")==digest(catalogue)
        and attestation.get("politique_sha256")==policy_fingerprint(catalogue,layout)
        and attestation.get("scopes_sha256")==digest(expected))
    return bound and attestation["contenu_controles_sha256"]==control_content(cx,layout)


def _catalogue(cx, layout):
    return rows(cx, f"SELECT * FROM {table(layout.dq,'regle')} ORDER BY rule_id")


def _manifest(cx, batch, layout):
    result = rows(cx, f"SELECT * FROM {table(layout.dq,'s4_manifeste')} WHERE batch_id=:b", {"b": batch})
    return result[0] if result else None


def owner_valid(owner, batch, manifest, gold_sha, history_sha):
    """Approbation liée au contenu et à l'historique ; aucune signature inventée."""
    if not isinstance(owner, dict):
        return False
    try:
        date.fromisoformat(owner.get("date_decision", ""))
    except (TypeError, ValueError):
        return False
    return bool(manifest and manifest.get("accepte") == 1 and
                owner.get("decision") == "ACCEPTE" and
                owner.get("batch_id") == batch and
                owner.get("configuration_sha256") == manifest.get("configuration_sha256") and
                owner.get("empreinte_gold") == gold_sha and
                owner.get("historique_sha256") == history_sha and
                all(isinstance(owner.get(k), str) and owner[k].strip()
                    for k in ("decideur", "date_decision", "signature", "justification")))


def _coverage(history, catalogue, layout):
    latest = {(m["couche"], m["rule_id"], m["table_logique"]): m
              for m in history["mesures"]}
    result = []
    for scope in required_scopes(catalogue, synthetic=layout.synthetic):
        m = latest.get((scope["couche"], scope["rule_id"], scope["table_logique"]))
        item = dict(scope)
        if not m:
            item.update(etat="NON_MESUREE", conforme=False)
        elif m["nb_testees"] <= 0:
            item.update(etat="POPULATION_ABSENTE", conforme=False, mesure_id=m["id"])
        elif m["nb_echecs"] < 0 or m["nb_echecs"] > m["nb_testees"]:
            item.update(etat="MESURE_INVALIDE", conforme=False, mesure_id=m["id"])
        else:
            # Comparaison entière exacte lorsque le seuil est à 100 %.
            good = (Decimal(m["nb_testees"]-m["nb_echecs"])*100 >=
                    Decimal(str(scope["seuil_min"]))*Decimal(m["nb_testees"]))
            item.update(etat="CONFORME" if good else "ECHEC", conforme=good,
                        mesure_id=m["id"], nb_testees=m["nb_testees"], nb_echecs=m["nb_echecs"])
        result.append(item)
    # Toute autre mesure finale bloquante réellement disponible est aussi contrôlée.
    present = {(m["couche"], m["rule_id"], m["table_logique"]) for m in result}
    for key, m in latest.items():
        if key in present or m["severite"] != "BLOQUANTE":
            continue
        expected_layer = {"B": "BRONZE", "S": "SILVER", "G": "GOLD"}.get(m["porte"])
        if m["couche"] != expected_layer and not (m["couche"] == "GOLD" and m["porte"] in ("S","G")):
            continue
        valid = m["nb_testees"] > 0 and 0 <= m["nb_echecs"] <= m["nb_testees"]
        good = valid and Decimal(m["nb_testees"]-m["nb_echecs"])*100 >= Decimal(str(m["seuil_min"]))*Decimal(m["nb_testees"])
        result.append({"rule_id": m["rule_id"], "couche": m["couche"],
                       "table_logique": m["table_logique"], "conforme": good,
                       "etat": "CONFORME" if good else "ECHEC", "mesure_id": m["id"],
                       "nb_testees": m["nb_testees"], "nb_echecs": m["nb_echecs"]})
    return result


def certify(engine, batch, owner=None, layout=Layout(), *, certificat_id=None, measurement_attestation=None):
    """Calcule et persiste un certificat. Le lot réel actuel doit rester NO_GO.

    `owner` est une décision humaine liée aux empreintes produites par l'audit.
    Un appel sans décision peut émettre NO_GO, jamais GO. Les décisions d'un
    environnement synthétique portent explicitement sa mention dans la preuve.
    """
    with coherent_connection(engine) as cx:
        assert_transactional(cx,layout)
        history = _history(cx, batch, layout)
        catalogue = _catalogue(cx, layout)
        gold = fingerprint_gold(cx, batch, layout)
        manifest = _manifest(cx, batch, layout)
        coverage = _coverage(history, catalogue, layout)
        approved = owner_valid(owner, batch, manifest, gold["sha256"], history["sha256"])
        motives = []
        attested=attestation_valid(cx,measurement_attestation,batch,layout,gold,history,catalogue,manifest)
        if not attested:
            motives.append("ATTESTATION_CONTROLES_COMPLETS_ABSENTE_OU_PERIMEE")
        integrity=_integrity(cx,layout,batch)
        if any(integrity.values()):
            motives.append("GOLD_ORPHELIN")
        if not coverage:
            motives.append("AUCUNE_REGLE_BLOQUANTE_ATTENDUE")
        if any(not c["conforme"] for c in coverage):
            motives.append("COUVERTURE_OU_CONFORMITE_BLOQUANTE_INSUFFISANTE")
        if history["mesures_invalides"]:
            motives.append("HISTORIQUE_INVALIDE")
        if not approved:
            motives.append("VALIDATION_OWNER_ABSENTE_OU_NON_LIEE_AUX_EMPREINTES")
        if any(t["lignes"] == 0 for t in gold["tables"].values()):
            motives.append("TABLE_GOLD_VIDE")
        warnings = [m for m in history["mesures"] if m["severite"] == "AVERTISSEMENT"
                    and (m["nb_testees"] == 0 or m["taux_conformite"] is None or
                         Decimal(str(m["taux_conformite"])) < Decimal(str(m["seuil_min"])))]
        # La décision est effectivement produite par SQL, sur les mêmes mesures.
        expected = required_scopes(catalogue, synthetic=layout.synthetic)
        # Inclure aussi tous les périmètres finaux bloquants supplémentaires.
        known = {(x["couche"],x["rule_id"],x["table_logique"]) for x in expected}
        for item in coverage:
            key = (item["couche"],item["rule_id"],item["table_logique"])
            if key not in known:
                rule = next(r for r in catalogue if r["rule_id"] == item["rule_id"])
                expected.append({**item, "seuil_min": str(rule["seuil_min"])})
        required_ids = {"RQ-%03d" % n for n in range(1,26)}
        complete = layout.synthetic or required_ids == {r["rule_id"] for r in catalogue}
        if not complete:
            motives.append("CATALOGUE_INCOMPLET")
        query_path = Path(__file__).resolve().parents[1]/"sql"/"S5_decision.sql"
        query = query_path.read_text().replace("{dq_history}", table(layout.dq,"dq_history"))
        sql_decision = dict(cx.execute(text(query), {
            "scopes": json_bytes(expected).decode(), "batch": batch,
            "owner_valide": int(approved),
            "historique_valide": int(not history["mesures_invalides"]),
            "gold_non_vide": int(all(t["lignes"] > 0 for t in gold["tables"].values())),
            "catalogue_complet": int(complete),"mesures_attestees":int(attested),
            "integrite_gold":int(not any(integrity.values()))}).mappings().one())
        assert sql_decision["decision"] == ("NO_GO" if motives else "GO")
        proof = {"batch_id": batch, "decision": sql_decision["decision"],
                 "decision_sql": sql_decision,
                 "synthetique": layout.synthetic, "motifs": motives,
                 "gold": gold, "history_sha256": history["sha256"],
                 "catalogue_sha256": digest(catalogue), "manifeste": manifest,
                 "politique_sha256": policy_fingerprint(catalogue,layout),
                 "attestation_controles":measurement_attestation if attested else None,
                 "provenance_mesures": ("CONTROLES_FIXTURE_EXECUTES_LIES" if layout.synthetic else "CONTROLES_EXECUTES_LIES") if attested else "HISTORIQUES_NON_LIES_AU_CONTENU_COURANT",
                 "integrite_gold":integrity,
                 "couverture": coverage, "avertissements": warnings,
                 "owner": owner if approved else None,
                 "schema_gold": layout.gold, "schema_dq": layout.dq,
                 "mapping": [list(m) for m in MAPPING]}
        proof_sha = digest(proof)
        cid = certificat_id or "S5-"+proof_sha[:27]
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,30}", cid):
            raise ValueError("Identifiant de certificat invalide")
        existing = rows(cx, f"SELECT preuve_sha256 FROM {table(layout.dq,'s5_certification')} WHERE certificat_id=:id", {"id": cid})
        if existing and existing[0]["preuve_sha256"] != proof_sha:
            raise ValueError("Certificat existant immuable : choisir un nouvel identifiant")
        if not existing:
            cx.execute(text(f"INSERT INTO {table(layout.dq,'s5_certification')} (certificat_id,batch_id,preuve,preuve_sha256) VALUES(:id,:b,:p,:h)"),
                       {"id": cid, "b": batch, "p": json_bytes(proof).decode(), "h": proof_sha})
            cx.execute(text(f"""INSERT INTO {table(layout.dq,'certificat_qualite')}
                (certificat_id,batch_id,nb_bloquantes_testees,nb_bloquantes_ok,empreinte_gold,decision,signataire,commentaire)
                VALUES(:id,:b,:n,:ok,:h,:decision,:sign,:comment)"""),
                       {"id": cid, "b": batch,
                        "n": sum(c["etat"] not in ("NON_MESUREE", "POPULATION_ABSENTE") for c in coverage),
                        "ok": sum(c["conforme"] for c in coverage), "h": gold["sha256"],
                        "decision": proof["decision"], "sign": owner["decideur"] if approved else None,
                        "comment": ("TEST_SYNTHETIQUE ; " if layout.synthetic else "")+" ; ".join(motives)[:450]})
        return {"certificat_id": cid, "preuve_sha256": proof_sha, **proof}


def _integrity(cx, layout, batch, target=False):
    schema = layout.target if target else layout.gold
    client, contract, claim = ("client", "contrat", "sinistre") if target else tuple(s for s, _ in MAPPING)
    queries = {
        "souscripteur": f"SELECT COUNT(*) FROM {table(schema,contract)} t LEFT JOIN {table(schema,client)} c ON c.cli_id=t.cli_souscripteur AND c._batch_id=t._batch_id WHERE t._batch_id=:b AND c.cli_id IS NULL",
        "assure": f"SELECT COUNT(*) FROM {table(schema,contract)} t LEFT JOIN {table(schema,client)} c ON c.cli_id=t.cli_assure AND c._batch_id=t._batch_id WHERE t._batch_id=:b AND t.cli_assure IS NOT NULL AND c.cli_id IS NULL",
        "contrat_sinistre": f"SELECT COUNT(*) FROM {table(schema,claim)} t LEFT JOIN {table(schema,contract)} c ON c.contrat_id=t.contrat_id AND c._batch_id=t._batch_id WHERE t._batch_id=:b AND c.contrat_id IS NULL",
    }
    return {name: cx.execute(text(sql), {"b": batch}).scalar_one()
            for name, sql in queries.items()}


def publish(engine, batch, certificat_id, layout=Layout(), *, fail_after=None):
    """Publication atomique du snapshot certifié, avec réconciliation avant commit.

    `fail_after` est une injection de panne réservée aux schémas de tests.
    Les tables doivent avoir été préparées explicitement avec prepare_target.
    """
    if fail_after is not None and not layout.synthetic:
        raise ValueError("Injection de panne uniquement dans un environnement synthétique")
    with coherent_connection(engine) as cx:
        assert_transactional(cx,layout)
        certs = rows(cx, f"SELECT * FROM {table(layout.dq,'certificat_qualite')} WHERE certificat_id=:id", {"id": certificat_id})
        if not certs:
            raise PublicationRefusee("CERTIFICAT_ABSENT")
        cert = certs[0]
        if cert["batch_id"] != batch:
            raise PublicationRefusee("LOT_DIFFERENT")
        if cert["decision"] != "GO":
            raise PublicationRefusee("CERTIFICAT_NO_GO")
        evidences = rows(cx, f"SELECT * FROM {table(layout.dq,'s5_certification')} WHERE certificat_id=:id", {"id": certificat_id})
        if not evidences:
            raise PublicationRefusee("PREUVE_CERTIFICAT_ABSENTE")
        evidence = evidences[0]
        proof = json.loads(evidence["preuve"])
        if digest(proof) != evidence["preuve_sha256"]:
            raise PublicationRefusee("PREUVE_CERTIFICAT_ALTEREE")
        if (proof["decision"] != "GO" or proof["batch_id"] != batch or
            proof["synthetique"] != layout.synthetic or proof["schema_gold"] != layout.gold or
            proof["schema_dq"] != layout.dq or proof["mapping"] != [list(m) for m in MAPPING]):
            raise PublicationRefusee("PERIMETRE_CERTIFICAT_INCOMPATIBLE")
        gold = fingerprint_gold(cx, batch, layout)
        if gold["sha256"] != cert["empreinte_gold"] or gold != proof["gold"]:
            raise PublicationRefusee("EMPREINTE_GOLD_DIFFERENTE")
        history = _history(cx, batch, layout)
        catalogue = _catalogue(cx, layout)
        manifest = _manifest(cx, batch, layout)
        if history["sha256"] != proof["history_sha256"] or digest(catalogue) != proof["catalogue_sha256"]:
            raise PublicationRefusee("MESURES_OU_CATALOGUE_MODIFIES")
        if proof.get("politique_sha256") != policy_fingerprint(catalogue,layout):
            raise PublicationRefusee("POLITIQUE_CERTIFICATION_MODIFIEE")
        if digest(manifest) != digest(proof["manifeste"]) or not owner_valid(proof["owner"], batch, manifest, gold["sha256"], history["sha256"]):
            raise PublicationRefusee("VALIDATION_OWNER_PERIMEE")
        if not attestation_valid(cx,proof.get("attestation_controles"),batch,layout,gold,history,catalogue,manifest):
            raise PublicationRefusee("ATTESTATION_CONTROLES_PERIMEE")
        if any(_integrity(cx, layout, batch).values()):
            raise PublicationRefusee("GOLD_ORPHELIN")
        for source, target_name in MAPPING:
            if columns(cx, layout.gold, source) != columns(cx, layout.target, target_name):
                raise PublicationRefusee("MAPPING_CIBLE_INCOMPATIBLE")
        for _,dst in MAPPING:
            if cx.execute(text(f"SELECT 1 FROM {table(layout.target,dst)} WHERE _batch_id IS NULL OR _batch_id<>:b LIMIT 1"),{"b":batch}).first():
                raise PublicationRefusee("CIBLE_AUTRE_LOT_NON_CERTIFIE")
        before = {dst: fingerprint_table(cx, layout.target, dst, batch)
                  for _, dst in MAPPING}
        # DELETE transactionnel ; jamais TRUNCATE ni DDL dans ce bloc.
        for _, dst in reversed(MAPPING):
            cx.execute(text(f"DELETE FROM {table(layout.target,dst)} WHERE _batch_id=:b"), {"b": batch})
        reconciliation = []
        for index, (source, dst) in enumerate(MAPPING, 1):
            names = gold["tables"][source]["colonnes"]
            fields = ",".join(ident(n) for n in names)
            binds = ",".join(":"+n for n in names)
            insert = text(f"INSERT INTO {table(layout.target,dst)} ({fields}) VALUES ({binds})")
            for page in table_pages(cx,layout.gold,source,names,batch):
                cx.execute(insert,[dict(r) for r in page])
            if fail_after == index:
                raise PublicationRefusee(f"PANNE_SIMULEE_APRES_{dst.upper()}")
            copied = fingerprint_table(cx, layout.target, dst, batch)
            expected = gold["tables"][source]
            if copied != expected:
                raise PublicationRefusee("RQ025_ECART_CONTENU")
            reconciliation.append({"table_gold": source, "table_cible": dst,
                                   "gold": expected, "cible": copied, "ecart": 0})
        if any(_integrity(cx, layout, batch, target=True).values()):
            raise PublicationRefusee("CIBLE_ORPHELINE")
        publication_id=uuid4().hex
        report={"batch_id":batch,"certificat_id":certificat_id,
                "synthetique":layout.synthetic,"publication":"CHARGEE",
                "reconciliation": reconciliation, "cible_avant": before,
                "tout_ou_rien":True,"empreinte_gold":gold["sha256"],"publication_id":publication_id}
        for item in reconciliation:
            cx.execute(text(f"""INSERT INTO {table(layout.dq,'dq_history')}
                (batch_id,couche,rule_id,table_cible,nb_testees,nb_echecs)
                VALUES(:b,'CRM','RQ-025',:t,:n,0)"""),
                {"b":batch,"t":item["table_cible"],"n":item["gold"]["lignes"]})
        cx.execute(text(f"""INSERT INTO {table(layout.dq,'s5_publication')}
            (publication_id,certificat_id,batch_id,empreinte_gold,preuve)
            VALUES(:p,:c,:b,:h,:r)"""),{"p":publication_id,"c":certificat_id,"b":batch,
                "h":gold["sha256"],"r":json_bytes(report).decode()})
        return report

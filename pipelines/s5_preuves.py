"""Preuves indépendantes S5 : lecture seule, empreintes et exports atomiques."""
from __future__ import annotations
import datetime as dt
import decimal
import hashlib
import json
import os
import re
from pathlib import Path
from sqlalchemy import text


def ident(value):
    if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', value):
        raise ValueError('Identifiant SQL invalide')
    return '`' + value + '`'


def value_tag(value):
    """Distingue NULL, vide, espaces, décimaux et dates sans perdre la précision."""
    if value is None:
        return ['null']
    if isinstance(value, bytes):
        return ['bytes', value.hex()]
    if isinstance(value, decimal.Decimal):
        return ['decimal', str(value)]
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return [type(value).__name__, value.isoformat()]
    return [type(value).__name__, value]


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=str).encode('utf-8')


def table_proof(conn, schema, table):
    """Empreinte d'un multiensemble complet : tri des SHA de lignes, doublons conservés."""
    columns = conn.execute(text('''SELECT column_name,column_type,is_nullable,collation_name
        FROM information_schema.columns WHERE table_schema=:s AND table_name=:t
        ORDER BY ordinal_position'''), {'s': schema, 't': table}).all()
    if not columns:
        raise ValueError(f'Table absente : {schema}.{table}')
    digest = hashlib.sha256(encoded([list(c) for c in columns]))
    hashes = []
    result = conn.execution_options(stream_results=True).execute(text(
        f'SELECT * FROM {ident(schema)}.{ident(table)}'))
    for row in result:
        hashes.append(hashlib.sha256(encoded([value_tag(v) for v in row])).digest())
    result.close()
    for value in sorted(hashes):
        digest.update(value)
    return {'lignes': len(hashes), 'sha256': digest.hexdigest()}


def snapshot(engine, schemas=('crm', 'cif', 'bronze', 'silver', 'gold', 'crm_cible')):
    """Snapshot cohérent des tables, y compris bronze et sources, hors vues."""
    with engine.connect().execution_options(isolation_level='REPEATABLE READ') as c:
        c.execute(text('START TRANSACTION WITH CONSISTENT SNAPSHOT'))
        tables = c.execute(text('''SELECT table_schema,table_name FROM information_schema.tables
            WHERE table_type='BASE TABLE' ORDER BY table_schema,table_name''')).all()
        data = {f'{s}.{t}': table_proof(c, s, t) for s, t in tables if s in schemas}
        c.rollback()
    return data


def write_report(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n')
    os.replace(temporary, path)


def protected_files(root):
    """Fichiers hors périmètre : vérifier qu'ils restent inchangés pendant S5."""
    names = ['AVANCEMENT.md', 'livrables/S4_silver_gold.md',
             'livrables/S5_certificat_publication.md', 'livrables/DOSSIER_GO_NOGO.md',
             'livrables/Livrable_Groupe_TD_AssurConnect.pptx',
             'livrables/S4_VALIDATION_DATA_OWNER.json', 'livrables/JOURNAL_DECISIONS.md']
    return {name: hashlib.sha256((Path(root) / name).read_bytes()).hexdigest()
            for name in names if (Path(root) / name).exists()}

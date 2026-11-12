"""Compléments US-29 reproductibles, sans reconstruire les couches nominales."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import zlib
from sqlalchemy import text
import s5_engineering as s5

SOURCES = [('crm','client','crm_client'),('crm','contrat','crm_contrat'),
 ('crm','sinistre','crm_sinistre'),('crm','type_contrat','crm_type_contrat'),
 ('cif','clients','cif_clients'),('cif','compte','cif_compte'),('cif','pays','cif_pays')]


def _payload(row):
    return json.dumps(list(row), ensure_ascii=False, separators=(',', ':')).encode()


def _business(cx, schema, name, names, batch=None):
    fields = ','.join(f'CAST({s5.ident(n)} AS CHAR CHARACTER SET utf8mb4)' for n in names)
    sql = f'SELECT {fields} FROM {s5.table(schema,name)}'
    if batch is not None:
        sql += ' WHERE _batch_id=:b'
    return cx.execute(text(sql), {'b': batch}).all()


def _signature(data):
    payloads = [_payload(row) for row in data]
    h = hashlib.sha256()
    for value in sorted(payloads):
        h.update(len(value).to_bytes(8,'big')); h.update(value)
    return {'lignes':len(data),'somme_crc32':sum(zlib.crc32(v)&0xffffffff for v in payloads),
            'sha256':h.hexdigest()}, Counter(payloads)


def complete_bronze(engine, batch):
    """Même conversion exacte que S1 ; ajoute des mesures S5 sans effacer S1/S4."""
    details, measures = [], []
    with s5.coherent_connection(engine) as cx:
        for schema, source, target in SOURCES:
            names = [c['name'] for c in s5.columns(cx,schema,source)]
            src, src_set = _signature(_business(cx,schema,source,names))
            bronze_data = _business(cx,'bronze',target,names,batch)
            bronze, bronze_set = _signature(bronze_data)
            ok = src == bronze and src_set == bronze_set
            meta = ['_batch_id','_source_system','_ingested_at','_row_hash']
            combined = _business(cx,'bronze',target,names+meta,batch)
            failures = 0
            for row in combined:
                business, values = row[:-4], row[-4:]
                failures += int(any(v is None or not v.strip() for v in values)
                    or values[0] != batch or values[1] != schema
                    or values[3] != hashlib.sha256(_payload(business)).hexdigest()[:16])
            details.append({'table_bronze':target,'source':f'{schema}.{source}',
                'source_preuve':src,'bronze_preuve':bronze,'contenu_exact_identique':ok,
                'metadonnees_testees':len(combined),'metadonnees_echecs':failures,
                'methode':'CAST CHAR UTF8 exact, multiensemble JSON, SHA256 et somme CRC32 ; hash ligne S1 revalidé'})
            for rule, n, ko in [('RQ-021',1,int(not ok)),('RQ-022',len(combined),failures)]:
                params={'b':batch,'r':rule,'t':'S5_'+target,'n':n,'e':ko}
                cx.execute(text('''INSERT INTO dq.dq_history
                    (batch_id,couche,rule_id,table_cible,nb_testees,nb_echecs)
                    VALUES(:b,'BRONZE',:r,:t,:n,:e)'''),params)
                measures.append({'rule_id':rule,'table_logique':target,'nb_testees':n,'nb_echecs':ko})
    return {'batch_id':batch,'mesure_le':datetime.now(timezone.utc).isoformat(),
            'details':details,'mesures':measures,'historiques_anterieurs_preserves':True}


def steward_export(engine, batch):
    """Export exhaustif : mesure historique, manquante ou justification technique."""
    history = s5.audit_history(engine,batch)
    with engine.connect() as cx:
        catalogue = s5._catalogue(cx,s5.Layout())
        config = s5._manifest(cx,batch,s5.Layout())
    matrix = []
    for rule in catalogue:
        for layer in ['BRONZE','SILVER','GOLD']:
            measures = [m for m in history['mesures'] if m['rule_id']==rule['rule_id'] and m['couche']==layer]
            reason = None
            if rule['rule_id'] in ('RQ-021','RQ-022') and layer != 'BRONZE':
                reason = 'Porte ingestion : réconciliation sources/bronze et métadonnées bronze seulement.'
            elif rule['rule_id']=='RQ-024' and layer!='SILVER':
                reason = 'Conservation bronze = silver + rejets S ; gold consolide les identités et exclut à la porte G.'
            elif rule['rule_id']=='RQ-023' and layer=='BRONZE':
                reason = 'Lineage silver/gold vers bronze ; bronze est la destination, non une couche aval.'
            elif rule['rule_id']=='RQ-025':
                reason = 'Réconciliation après publication CRM : nominal non publié, aucun résultat CRM inventé.'
            state = 'MESURE_DISPONIBLE' if measures else ('NON_APPLICABLE_TECHNIQUE' if reason else 'NON_MESUREE')
            matrix.append({'rule_id':rule['rule_id'],'dimension':rule['dimension'],
                'severite':rule['severite'],'couche':layer,'etat':state,
                'raison':reason,'mesures':measures,
                'consequence': 'À faire qualifier par le Steward ; une absence bloquante à sa porte interdit GO.' if not measures else
                    'Résultats dq_history relus : préfixe S5_ = remesures S5, autres préfixes = mesures historiques non liées au contenu/configuration actuels.'})
    return {'batch_id':batch,'configuration_sha256':config['configuration_sha256'],
            'historique':history,'matrice':matrix,
            'limites':['Aucune courbe US-30 ni fiche US-34 produite.',
            'Taux SQL historiques arrondis à 0,001 point ; calculs de seuil sur effectifs entiers.',
            'Les anciennes mesures S4 sont datées et ne constituent pas des remesures S5.',
            'Le rôle CIF absent rend RQ-003/009/015/016 non applicables aux fiches CIF ; aucune assimilation à 100%.',
            'Périmètres multi-tables et signatures RQ-019 conservés séparément ; aucun taux moyen sans dénominateur.']}


def measure_gold_residuals(engine, batch):
    """Signatures connues reliées ; absences mesurées séparément par RQ-023."""
    queries = {}
    for nature, cols in [('PP',['identite_normalisee','prenom_normalise','date_naissance']),
                        ('PM',['identite_normalisee','cp','adresse_normalisee'])]:
        fields=','.join('s.'+s5.ident(c) for c in cols)
        nonnull=' AND '.join('s.'+s5.ident(c)+' IS NOT NULL' for c in cols)
        queries[('RQ-019','identites_'+nature)] = f'''SELECT COUNT(*) n, COALESCE(SUM(clis>1),0) ko FROM (
            SELECT COUNT(DISTINCT g.cli_id) clis FROM silver.client s
            LEFT JOIN gold.xref_identifiants x ON x.silver_row_id=s.silver_row_id
              AND x.bronze_row_id=s.bronze_row_id AND x.source_systeme=s.source_systeme
              AND x.source_id=s.source_id
            LEFT JOIN gold.client_unique g ON g.cli_id=x.cli_id AND g._batch_id=s._batch_id
            WHERE s._batch_id=:b AND s.nature_personne='{nature}' AND {nonnull}
            GROUP BY {fields} HAVING COUNT(DISTINCT g.cli_id)>0) signatures'''
    for name,cols in [('nom_cp_naissance_tel',['nom_reference','cp','date_naissance','telephone']),
                      ('nom_email',['nom_reference','email'])]:
        fields=','.join(s5.ident(c) for c in cols)
        nonnull=' AND '.join(s5.ident(c)+' IS NOT NULL' for c in cols)
        queries[('RQ-019','signature_'+name)] = f'''SELECT COUNT(*) n,COALESCE(SUM(clis>1),0) ko FROM (
            SELECT COUNT(DISTINCT cli_id) clis FROM gold.client_unique
            WHERE _batch_id=:b AND {nonnull} GROUP BY {fields}) signatures'''
    queries[('RQ-016','client_unique')] = '''SELECT COUNT(*) n,
        COALESCE(SUM(NOT EXISTS(SELECT 1 FROM gold.contrat_certifie c
          WHERE c.cli_souscripteur=g.cli_id AND c._batch_id=g._batch_id)),0) ko
        FROM gold.client_unique g WHERE g._batch_id=:b
          AND g.statut_client IN ('ACTIF','INACTIF','A_REVOIR')'''
    results=[]
    with s5.coherent_connection(engine) as cx:
        for (rule,scope),query in queries.items():
            n,ko=map(int,cx.execute(text(query),{'b':batch}).one())
            cx.execute(text('''INSERT INTO dq.dq_history(batch_id,couche,rule_id,table_cible,nb_testees,nb_echecs)
                VALUES(:b,'GOLD',:r,:t,:n,:e)'''),{'b':batch,'r':rule,'t':'S5_'+scope,'n':n,'e':ko})
            results.append({'batch_id':batch,'couche':'GOLD','rule_id':rule,'table_logique':scope,
                            'nb_testees':n,'nb_echecs':ko,'requete':query,
                            'mesure_le':datetime.now(timezone.utc).isoformat()})
    return results


def lineage_queries(gold='gold', silver='silver', bronze='bronze', *, quarantine_dq=None):
    """Populations complètes avec LEFT JOIN : aucun absent ne disparaît."""
    queries={}
    queries['silver_xref_gold']=f'''SELECT COUNT(*) n,COALESCE(SUM(x.cli_id IS NULL OR g.cli_id IS NULL),0) ko
        FROM {s5.table(silver,'client')} s
        LEFT JOIN {s5.table(gold,'xref_identifiants')} x ON x.silver_row_id=s.silver_row_id
          AND x.bronze_row_id=s.bronze_row_id AND x.source_systeme=s.source_systeme AND x.source_id=s.source_id
        LEFT JOIN {s5.table(gold,'client_unique')} g ON g.cli_id=x.cli_id AND g._batch_id=s._batch_id
        WHERE s._batch_id=:b'''
    if quarantine_dq is not None:
        # Un absent n'est justifié que par le plan APPLIQUE de la configuration
        # courante, la référence source complète et son rejet RQ019 précis.
        dq = quarantine_dq
        queries['silver_xref_gold'] = f'''SELECT COUNT(*) n,
          COALESCE(SUM((x.cli_id IS NULL OR g.cli_id IS NULL) AND q.silver_row_id IS NULL),0) ko,
          COALESCE(SUM(q.silver_row_id IS NOT NULL),0) exclusions_rq019
          FROM {s5.table(silver,'client')} s
          LEFT JOIN {s5.table(gold,'xref_identifiants')} x ON x.silver_row_id=s.silver_row_id
            AND x.bronze_row_id=s.bronze_row_id AND x.source_systeme=s.source_systeme AND x.source_id=s.source_id
          LEFT JOIN {s5.table(gold,'client_unique')} g ON g.cli_id=x.cli_id AND g._batch_id=s._batch_id
          LEFT JOIN (
            SELECT DISTINCT ref.source_systeme,ref.source_id,ref.bronze_row_id,ref.silver_row_id,b._batch_id
            FROM {s5.table(dq,'rq019_reference_xref_identifiants')} ref
            JOIN {s5.table(dq,'rq019_reference_client_unique')} b ON b.cli_id=ref.cli_id
            JOIN {s5.table(dq,'rq019_etat')} e ON e.batch_id=b._batch_id AND e.etat='APPLIQUE'
            JOIN {s5.table(dq,'s4_manifeste')} m ON m.batch_id=e.batch_id
              AND m.configuration_sha256=e.configuration_sha256
            JOIN {s5.table(dq,'rejets')} r ON r.batch_id=b._batch_id AND r.entite='client'
              AND r.source_systeme=ref.source_systeme AND r.bronze_row_id=ref.bronze_row_id
              AND r.rule_id='RQ-019' AND r.porte='G' AND r.motif='RQ019_V1_IDENTITE_INCERTAINE'
            WHERE JSON_CONTAINS(JSON_EXTRACT(e.plan_json,'$.excluded_cli'),JSON_QUOTE(ref.cli_id))=1
          ) q ON q.silver_row_id=s.silver_row_id AND q.bronze_row_id=s.bronze_row_id
             AND q.source_systeme=s.source_systeme AND q.source_id=s.source_id AND q._batch_id=s._batch_id
          WHERE s._batch_id=:b'''
    for origin,tb,idcol in [('crm','crm_client','client_id'),('cif','cif_clients','column0')]:
        queries['xref_'+origin]=f'''SELECT COUNT(*) n,COALESCE(SUM(s.silver_row_id IS NULL OR b.bronze_row_id IS NULL OR g.cli_id IS NULL),0) ko
          FROM {s5.table(gold,'xref_identifiants')} x
          LEFT JOIN {s5.table(silver,'client')} s ON s.silver_row_id=x.silver_row_id
            AND s.bronze_row_id=x.bronze_row_id AND s.source_systeme=x.source_systeme
            AND s.source_id=x.source_id AND s._batch_id=:b
          LEFT JOIN {s5.table(bronze,tb)} b ON b.bronze_row_id=x.bronze_row_id
            AND b.{s5.ident(idcol)}=x.source_id AND b._batch_id=:b
          LEFT JOIN {s5.table(gold,'client_unique')} g ON g.cli_id=x.cli_id AND g._batch_id=:b
          WHERE x.source_systeme='{origin}' '''
    for target,ts,tb,idcol in [('contrat_certifie','contrat','crm_contrat','contrat_id'),
                             ('sinistre_certifie','sinistre','crm_sinistre','sinistre_id')]:
        queries[target]=f'''SELECT COUNT(*) n,COALESCE(SUM(s.silver_row_id IS NULL OR b.bronze_row_id IS NULL),0) ko
          FROM {s5.table(gold,target)} g LEFT JOIN {s5.table(silver,ts)} s
          ON s.silver_row_id=g.silver_row_id AND s.bronze_row_id=g.bronze_row_id AND s._batch_id=g._batch_id
          LEFT JOIN {s5.table(bronze,tb)} b ON b.bronze_row_id=g.bronze_row_id
          AND b._batch_id=g._batch_id AND b.{s5.ident(idcol)}=g.{s5.ident(idcol)} WHERE g._batch_id=:b'''
    queries['client_unique']=f'''SELECT COUNT(*) n,COALESCE(SUM(NOT EXISTS(
        SELECT 1 FROM {s5.table(gold,'xref_identifiants')} x
        LEFT JOIN {s5.table(silver,'client')} s ON s.silver_row_id=x.silver_row_id
          AND s.bronze_row_id=x.bronze_row_id AND s.source_systeme=x.source_systeme AND s.source_id=x.source_id
        WHERE x.cli_id=g.cli_id AND s._batch_id=g._batch_id)),0) ko
        FROM {s5.table(gold,'client_unique')} g WHERE g._batch_id=:b'''
    return queries


def measure_lineage(engine,batch):
    results=[]
    with s5.coherent_connection(engine) as cx:
        s5.assert_transactional(cx,s5.Layout())
        required = {'rq019_etat','rq019_reference_xref_identifiants','rq019_reference_client_unique'}
        present = set(cx.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='dq'")).scalars())
        if present & required and not required <= present:
            raise ValueError('État de résolution RQ019 incomplet : lineage refusé')
        quarantine_dq = 'dq' if required <= present else None
        for scope,query in lineage_queries(quarantine_dq=quarantine_dq).items():
            measured = cx.execute(text(query),{'b':batch}).mappings().one()
            n,ko = int(measured['n']),int(measured['ko'])
            cx.execute(text('''INSERT INTO dq.dq_history(batch_id,couche,rule_id,table_cible,nb_testees,nb_echecs)
                VALUES(:b,'GOLD','RQ-023',:t,:n,:e)'''),{'b':batch,'t':'S5_'+scope,'n':n,'e':ko})
            results.append({'batch_id':batch,'couche':'GOLD','rule_id':'RQ-023','table_logique':scope,
                'nb_testees':n,'nb_echecs':ko,'requete':query,'mesure_le':datetime.now(timezone.utc).isoformat(),
                'exclusions_rq019_justifiees':int(measured.get('exclusions_rq019',0)),
                'population':'Toutes les lignes silver : lien gold ou quarantaine RQ019 vérifiée ; les exclus ne sont pas des identités réparées.' if scope=='silver_xref_gold' and quarantine_dq else 'Liens des lignes retenues, LEFT JOIN par origine et lot'})
    return results

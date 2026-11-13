"""Résolution RQ-019 candidate : aucune approbation ni publication implicite.

Import sans effet. Les références en base sont conservées pour un retour contrôlé.
Les suppressions, insertions, rejets, manifeste et état sont une seule transaction.
"""
from collections import Counter, defaultdict
from datetime import date
from itertools import combinations, product
from pathlib import Path
import csv
import hashlib
import json
import re

from rapidfuzz import fuzz
from sqlalchemy import text
import s5_engineering as s5

BATCH = 'L-2026-10-01'
TABLES = ('client_unique', 'xref_identifiants', 'contrat_certifie', 'sinistre_certifie')
PREFIX = 'RQ019_V1_'
LABEL_SHA = '4345596b5d14d8ceab23be3c9a8db8b6f5ed263a57b178637a6c14b941e0c5a9'
BASE_CONFIG = 'eed9d4937fbdd7ef476637ed8bde0f722421a5d7a18804f0a5d04b972e28ba61'
CONFIG = {'version':'RQ019_V1', 'reference':BASE_CONFIG, 'seuil_auto':90,
          'fusion':'complete-link ; garde-fous S4 et labels négatifs ; aucune transitivité supposée',
          'incertitude':'quarantaine G de toutes les identités impliquées et dépendances',
          'acceptation_owner':False,'labels_sha256':LABEL_SHA,
          'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
CONFIG_SHA = s5.digest(CONFIG)


def key(r):
    return (r['source_systeme'], r['source_id'])


def pairkey(a,b):
    return frozenset((key(a),key(b)))


def compatible_records(a,b,negative_pairs=frozenset()):
    """Mêmes garde-fous complets que S4 ; un label positif ne les contourne pas."""
    if pairkey(a,b) in negative_pairs:
        return False
    nature=a.get('nature_personne')
    if nature not in ('PP','PM') or nature != b.get('nature_personne'):
        return False
    for col in ('pays_iso','ville_normalisee'):
        av,bv=a.get(col),b.get(col)
        if av is not None and bv is not None and str(av).strip().upper()!=str(bv).strip().upper():
            return False
    if nature=='PP':
        da,db=a.get('date_naissance'),b.get('date_naissance')
        if da is None or db is None or str(da)!=str(db):
            return False
        pa,pb=a.get('prenom_normalise'),b.get('prenom_normalise')
        if pa is None or pb is None:
            prenom=50
        elif re.fullmatch(r'[A-Z]\.?',pa) or re.fullmatch(r'[A-Z]\.?',pb):
            prenom=100 if pa[0]==pb[0] else 0
        else:
            prenom=fuzz.ratio(pa,pb)
        score=.4*fuzz.ratio(a.get('identite_normalisee') or '',b.get('identite_normalisee') or '')+.3*prenom+30
    else:
        score=fuzz.token_set_ratio(a.get('identite_normalisee') or '',b.get('identite_normalisee') or '')
    return score>=90


def signatures(clients,xrefs,gold):
    """Les quatre dénominateurs ne sont pas additionnables."""
    xmap={r['silver_row_id']:r['cli_id'] for r in xrefs}
    populations={}
    for nature,cols in [('PP',('identite_normalisee','prenom_normalise','date_naissance')),
                         ('PM',('identite_normalisee','cp','adresse_normalisee'))]:
        groups=defaultdict(set); excluded=0
        for r in clients:
            if r.get('nature_personne')!=nature: continue
            if r['silver_row_id'] not in xmap or any(r.get(c) is None for c in cols):
                excluded+=1;continue
            groups[tuple(r[c] for c in cols)].add(xmap[r['silver_row_id']])
        populations['identites_'+nature]=(groups,excluded)
    for name,cols in [('nom_cp_naissance_tel',('nom_reference','cp','date_naissance','telephone')),
                      ('nom_email',('nom_reference','email'))]:
        groups=defaultdict(set);excluded=0
        for r in gold:
            if any(r.get(c) is None for c in cols):excluded+=1;continue
            groups[tuple(r[c] for c in cols)].add(r['cli_id'])
        populations['signature_'+name]=(groups,excluded)
    return populations


def signature_summary(clients,xrefs,gold):
    return [{'rule_id':'RQ-019','table_logique':scope,'nb_testees':len(groups),
             'nb_echecs':sum(len(v)>1 for v in groups.values()),'lignes_exclues':excluded,
             'taux':100*(1-sum(len(v)>1 for v in groups.values())/len(groups)) if groups else None}
            for scope,(groups,excluded) in signatures(clients,xrefs,gold).items()]


def build_plan(clients,xrefs,gold,labels):
    members=defaultdict(list)
    byid={r['silver_row_id']:r for r in clients}
    for x in xrefs:
        members[x['cli_id']].append(byid[x['silver_row_id']])
    negative={frozenset(((r['gauche_systeme'],r['gauche_id']),(r['droite_systeme'],r['droite_id'])))
              for r in labels if str(r['meme_personne'])=='0'}
    parent={r['cli_id']:r['cli_id'] for r in gold}
    def root(x):
        while parent[x]!=x:x=parent[x]
        return x
    collisions=[]
    for scope,(groups,_) in signatures(clients,xrefs,gold).items():
        for values,ids in groups.items():
            if len(ids)>1:
                collisions.append((scope,s5.digest(values),sorted(ids)))
    classifications=[];merges=[]
    for scope,sig,ids in sorted(collisions):
        roots=sorted({root(i) for i in ids})
        if len(roots)==1:continue
        full=[r for cli in roots for r in members[cli]]
        allowed=all(compatible_records(a,b,negative) for a,b in combinations(full,2))
        refs=sorted([{'source_systeme':r['source_systeme'],'source_id':r['source_id'],
                      'bronze_row_id':r['bronze_row_id'],'silver_row_id':r['silver_row_id']} for r in full],
                    key=lambda r:(r['source_systeme'],r['source_id']))
        classifications.append({'scope':scope,'signature_sha256':sig,'cli':roots,'sources':refs,
                                'decision':'CONSOLIDATION_TECHNIQUE' if allowed else 'INCERTITUDE_QUARANTAINE',
                                'groupe_complet_verifie':True})
        if allowed:
            winner=min(roots)
            for loser in roots:
                if loser==winner:continue
                parent[loser]=winner; members[winner]+=members.pop(loser)
                merges.append({'de':loser,'vers':winner})
    mapping={i:root(i) for i in parent}
    # Une collision non résolue exclut tous ses membres, y compris les racines fusionnées.
    excluded=set()
    for _,_,ids in collisions:
        roots={root(i) for i in ids}
        if len(roots)>1:excluded.update(roots)
    excluded_old=sorted(i for i in parent if root(i) in excluded)
    plan={'mapping':mapping,'excluded_cli':excluded_old,'merges':merges,'classifications':classifications,
          'source_roles':{x['cli_id']:False for x in xrefs},'configuration_sha256':CONFIG_SHA,
          'silver_sha256':s5.digest(sorted(clients,key=lambda r:r['silver_row_id'])),
          'input_sha256':s5.digest({'clients':sorted(clients,key=lambda r:r['silver_row_id']),
              'xrefs':sorted(xrefs,key=lambda r:r['silver_row_id']),
              'gold':sorted(gold,key=lambda r:r['cli_id']), 'labels':labels})}
    for x in xrefs:
        r=byid[x['silver_row_id']]
        if r.get('source_systeme')=='crm' and r.get('type_personne')=='souscripteur':
            plan['source_roles'][x['cli_id']]=True
    plan['survivors']={}
    for winner in sorted({m['vers'] for m in merges}):
        winner=root(winner)
        group=members[winner]
        def survivor(col,pattern=None,complete=False):
            values=[r for r in group if r.get(col) is not None and
                    (pattern is None or re.fullmatch(pattern,str(r[col])))]
            if not values:return None
            count=Counter(r[col] for r in values)
            return min(values,key=lambda r:(-count[r[col]],-len(str(r[col])) if complete else 0,
                       0 if r['source_systeme']=='crm' else 1,str(r[col])))[col]
        name=survivor('identite_normalisee',complete=True)
        first=survivor('prenom_normalise',complete=True)
        blocks=[dict(r,bloc_adresse='|'.join(str(r.get(c)) for c in ('cp','ville_normalisee','pays_iso'))) for r in group]
        oldgroup=group;group=blocks;address=survivor('bloc_adresse');group=oldgroup
        cp,city,country=[None if v in ('None','nan','<NA>') else v for v in address.split('|')]
        plan['survivors'][winner]={'nom_reference':(name or '')+' '+first if first is not None else name,
            'date_naissance':survivor('date_naissance'),'cp':cp,'ville':city,'pays_iso':country,
            'telephone':survivor('telephone_normalise',r'0[1-9]\d{8}|\+\d{8,15}'),
            'email':survivor('email_normalise',r'[^@\s]+@[^@\s]+\.[a-z]{2,}')}
    # La survie peut créer une nouvelle signature secondaire : fermer la quarantaine.
    while True:
        retained=[dict(r,**plan['survivors'].get(r['cli_id'],{})) for r in gold
                  if r['cli_id'] not in plan['excluded_cli'] and mapping[r['cli_id']]==r['cli_id']]
        xr=[dict(r,cli_id=mapping[r['cli_id']]) for r in xrefs if r['cli_id'] not in plan['excluded_cli']]
        pending=set()
        for scope,(groups,_) in signatures(clients,xr,retained).items():
            for values,ids in groups.items():
                if len(ids)>1:
                    pending.update(ids)
                    classifications.append({'scope':scope,'signature_sha256':s5.digest(values),
                        'cli':sorted(ids),'decision':'INCERTITUDE_APRES_SURVIE_QUARANTAINE',
                        'groupe_complet_verifie':True})
        if not pending:break
        plan['excluded_cli']=sorted(set(plan['excluded_cli'])|{i for i in mapping if mapping[i] in pending})
    plan['sha256']=s5.digest(plan)
    return plan


def fingerprints(cx,gold='gold',dq='dq'):
    return {t:s5.fingerprint_table(cx,gold,t) for t in TABLES} | {
        'rejets':s5.fingerprint_table(cx,dq,'rejets'),
        'manifeste':s5.fingerprint_table(cx,dq,'s4_manifeste')}


def prepare(cx,gold='gold',dq='dq'):
    """DDL additive seulement ; jamais au milieu de la transaction métier."""
    for name in TABLES:
        cx.execute(text(f'CREATE TABLE IF NOT EXISTS {s5.table(dq,"rq019_reference_"+name)} LIKE {s5.table(gold,name)}'))
    for name in ('rejets','s4_manifeste'):
        target='manifeste' if name=='s4_manifeste' else name
        cx.execute(text(f'CREATE TABLE IF NOT EXISTS {s5.table(dq,"rq019_reference_"+target)} LIKE {s5.table(dq,name)}'))
    cx.execute(text(f'''CREATE TABLE IF NOT EXISTS {s5.table(dq,'rq019_etat')} (
        batch_id VARCHAR(20) PRIMARY KEY, etat VARCHAR(30) NOT NULL,
        plan_sha256 CHAR(64) NOT NULL, reference_json LONGTEXT NOT NULL,
        courant_json LONGTEXT NOT NULL, configuration_sha256 CHAR(64) NOT NULL,
        bilan_json LONGTEXT NOT NULL, plan_json LONGTEXT NOT NULL) ENGINE=InnoDB'''))


def _read(cx,schema,name):
    return s5.rows(cx,f'SELECT * FROM {s5.table(schema,name)}')


def _insert(cx,schema,name,data):
    if not data:return
    cols=list(data[0]); fields=','.join(s5.ident(c) for c in cols)
    stmt=text(f'INSERT INTO {s5.table(schema,name)} ({fields}) VALUES ('+','.join(':'+c for c in cols)+')')
    for i in range(0,len(data),1000):cx.execute(stmt,data[i:i+1000])


def _target(reference,plan,batch):
    mapping=plan['mapping'];excluded=set(plan['excluded_cli'])
    clients={r['cli_id']:dict(r) for r in reference['client_unique'] if r['cli_id'] not in excluded}
    xrefs=[dict(x,cli_id=mapping[x['cli_id']]) for x in reference['xref_identifiants'] if x['cli_id'] not in excluded]
    # Attributs de référence déjà issus de la survie S4 ; seules fusions à naissance/géographie compatibles.
    # Le survivant déterministe reste la plus petite CLI, sans inventer de valeur source.
    for old,winner in mapping.items():
        if old!=winner:clients.pop(old,None)
    counts=Counter(x['cli_id'] for x in xrefs)
    for i,c in clients.items():
        c.update(plan.get('survivors',{}).get(i,{}))
        c['nb_identifiants_source']=counts[i]
    rejects=[]
    def reject(entity,r,motif,source='crm'):
        rejects.append({'batch_id':batch,'entite':entity,'source_systeme':source,
                        'bronze_row_id':r['bronze_row_id'],'rule_id':'RQ-019','porte':'G','motif':PREFIX+motif})
    for x in reference['xref_identifiants']:
        if x['cli_id'] in excluded:reject('client',x,'IDENTITE_INCERTAINE',x['source_systeme'])
    contracts=[]
    for r in reference['contrat_certifie']:
        r=dict(r)
        if r['cli_souscripteur'] in excluded or r['cli_assure'] in excluded:
            reject('contrat',r,'DEPENDANCE_CLIENT');continue
        r['cli_souscripteur']=mapping[r['cli_souscripteur']]
        if r['cli_assure'] is not None:r['cli_assure']=mapping[r['cli_assure']]
        contracts.append(r)
    keep={r['contrat_id'] for r in contracts};claims=[]
    for r in reference['sinistre_certifie']:
        if r['contrat_id'] not in keep:reject('sinistre',r,'DEPENDANCE_CONTRAT')
        else:claims.append(dict(r))
    subscribers={r['cli_souscripteur'] for r in contracts}
    insured={r['cli_assure'] for r in contracts if r['cli_assure'] is not None}
    ref=date.fromisoformat(batch[2:]);cot=date(2026,7,1)
    active={r['cli_souscripteur'] for r in contracts if r['date_debut']<=ref<=r['date_fin']
            and r['date_derniere_cotisation'] is not None and r['date_derniere_cotisation']>=cot}
    former={mapping[i] for i,v in plan['source_roles'].items() if v and i not in excluded}
    for i,r in clients.items():
        r['statut_client']='ACTIF' if i in active else 'INACTIF' if i in subscribers else 'ASSURE' if i in insured else 'A_REVOIR' if i in former else 'PROSPECT'
        r['motif_revue']='ANCIEN_SOUSCRIPTEUR_SANS_CONTRAT_CERTIFIE' if r['statut_client']=='A_REVOIR' else None
    return {'client_unique':list(clients.values()),'xref_identifiants':xrefs,
            'contrat_certifie':contracts,'sinistre_certifie':claims},rejects


def _verify_reference(cx, before, dq):
    actual={name:s5.fingerprint_table(cx,dq,'rq019_reference_'+name) for name in TABLES}
    actual['rejets']=s5.fingerprint_table(cx,dq,'rq019_reference_rejets')
    actual['manifeste']=s5.fingerprint_table(cx,dq,'rq019_reference_manifeste')
    if actual!=before:
        raise ValueError('Référence de restauration altérée : refus')


def apply(engine,plan,batch=BATCH,fail_at=None,gold='gold',dq='dq',restore=False,_test_auditor=None):
    """Référence protégée, même plan uniquement ; panne injectée avant commit."""
    if _test_auditor is not None and (gold,dq)==('gold','dq'):
        raise ValueError('Auditeur injecté interdit sur le nominal')
    if (gold,dq)!=('gold','dq') and not all(n.startswith('s5_test_') for n in (gold,dq)):
        raise ValueError('Schémas alternatifs non isolés')
    if s5.digest({k:v for k,v in plan.items() if k!='sha256'})!=plan['sha256']:
        raise ValueError('Plan altéré')
    with engine.connect() as cx:
        if cx.execute(text("SELECT GET_LOCK('s4_construction',0)")).scalar()!=1:raise RuntimeError('Construction concurrente')
        try:
            prepare(cx,gold,dq);cx.commit()
            with cx.begin():
                states=s5.rows(cx,f'SELECT * FROM {s5.table(dq,"rq019_etat")} WHERE batch_id=:b FOR UPDATE',{'b':batch})
                current=fingerprints(cx,gold,dq)
                for schema,names in [(gold,TABLES),(dq,('rejets','s4_manifeste','rq019_etat'))]:
                    for name in names:
                        storage=cx.execute(text('SELECT ENGINE FROM information_schema.tables WHERE table_schema=:s AND table_name=:t'),{'s':schema,'t':name}).scalar_one()
                        if storage!='InnoDB':raise ValueError('Table non transactionnelle : '+name)
                if gold=='gold' and s5.digest(sorted(_read(cx,'silver','client'),key=lambda r:r['silver_row_id']))!=plan['silver_sha256']:
                    raise ValueError('Silver modifié depuis le plan')
                if states:
                    state=states[0]
                    if state['plan_sha256']!=plan['sha256']:raise ValueError('Plan différent de la référence')
                    if s5.digest(current)!=s5.digest(json.loads(state['courant_json'])):raise ValueError('Contenu inattendu : refus')
                    _verify_reference(cx,json.loads(state['reference_json']),dq)
                    if state['etat']==('REFERENCE' if restore else 'APPLIQUE'):
                        return {'rejeu':True,'etat':state['etat'],'empreintes':current,'bilan':json.loads(state['bilan_json'])}
                    before=json.loads(state['reference_json'])
                else:
                    if restore:raise ValueError('Aucune référence disponible')
                    manifest=_read(cx,dq,'s4_manifeste')
                    if gold=='gold' and (len(manifest)!=1 or manifest[0]['configuration_sha256']!=BASE_CONFIG):
                        raise ValueError('Configuration historique inattendue')
                    before=current
                    if gold=='gold':historical_audit(cx,Path(__file__).resolve().parent.parent)
                    for name in TABLES:
                        if _read(cx,dq,'rq019_reference_'+name):raise ValueError('Référence orpheline non vide')
                        cx.execute(text(f'INSERT INTO {s5.table(dq,"rq019_reference_"+name)} SELECT * FROM {s5.table(gold,name)}'))
                    for name,target in [('rejets','rejets'),('s4_manifeste','manifeste')]:
                        if _read(cx,dq,'rq019_reference_'+target):raise ValueError('Référence orpheline non vide')
                        cx.execute(text(f'INSERT INTO {s5.table(dq,"rq019_reference_"+target)} SELECT * FROM {s5.table(dq,name)}'))
                reference={t:_read(cx,dq,'rq019_reference_'+t) for t in TABLES}
                if any(r['_batch_id']!=batch for t in TABLES if t!='xref_identifiants' for r in reference[t]):
                    raise ValueError('Autre lot présent : refus')
                if gold=='gold':
                    labelpath=Path(__file__).resolve().parent.parent/'data/referentiels/paires_etiquetees.csv'
                    if hashlib.sha256(labelpath.read_bytes()).hexdigest()!=LABEL_SHA:raise ValueError('Labels modifiés')
                    actual_input=s5.digest({'clients':sorted(_read(cx,'silver','client'),key=lambda r:r['silver_row_id']),
                        'xrefs':sorted(reference['xref_identifiants'],key=lambda r:r['silver_row_id']),
                        'gold':sorted(reference['client_unique'],key=lambda r:r['cli_id']),
                        'labels':list(csv.DictReader(labelpath.open()))})
                    if actual_input!=plan['input_sha256']:raise ValueError('Entrées du plan modifiées')
                _verify_reference(cx,before,dq)
                original_rejects=_read(cx,dq,'rq019_reference_rejets')
                original_manifest=_read(cx,dq,'rq019_reference_manifeste')
                target,new_rejects=(reference,[]) if restore else _target(reference,plan,batch)
                for t in reversed(TABLES):cx.execute(text(f'DELETE FROM {s5.table(gold,t)}'))
                cx.execute(text(f'DELETE FROM {s5.table(dq,"rejets")}'))
                if fail_at=='after_delete':raise RuntimeError('Panne injectée after_delete')
                for t in TABLES:_insert(cx,gold,t,target[t])
                _insert(cx,dq,'rejets',original_rejects)
                _insert(cx,dq,'rejets',new_rejects)
                if fail_at=='after_insert':raise RuntimeError('Panne injectée after_insert')
                if restore:
                    cx.execute(text(f'DELETE FROM {s5.table(dq,"s4_manifeste")}'))
                    _insert(cx,dq,'s4_manifeste',original_manifest)
                else:
                    cx.execute(text(f'''UPDATE {s5.table(dq,'s4_manifeste')}
                        SET configuration_sha256=:h, etat='CANDIDAT_RQ019_NON_ACCEPTE',accepte=0 WHERE batch_id=:b'''),{'h':plan['configuration_sha256'],'b':batch})
                after=fingerprints(cx,gold,dq)
                bilan={'nouveaux_rejets':dict(Counter(r['entite'] for r in new_rejects)),
                       'volumes':{t:len(target[t]) for t in TABLES},'configuration_sha256':plan['configuration_sha256']}
                params={'b':batch,'e':'REFERENCE' if restore else 'APPLIQUE','p':plan['sha256'],
                        'r':json.dumps(before),'c':json.dumps(after),'h':plan['configuration_sha256'],'j':json.dumps(bilan),'plan':json.dumps(plan,default=str)}
                cx.execute(text(f'''INSERT INTO {s5.table(dq,'rq019_etat')}
                    VALUES(:b,:e,:p,:r,:c,:h,:j,:plan) ON DUPLICATE KEY UPDATE etat=:e,courant_json=:c,bilan_json=:j,plan_json=:plan'''),params)
                # Contrôles sur l'état non commité : un échec fait aussi annuler référence et manifeste.
                _validate_target(target,new_rejects,reference)
                if gold=='gold' or _test_auditor is not None:
                    measured,conserved=checks(cx,_read(cx,'silver','client'),batch) if gold=='gold' else _test_auditor(cx)
                    blocking=[m for m in measured if m['nb_echecs'] and m['rule_id']!='RQ-016']
                    if blocking and not restore:raise AssertionError('Contrôles finaux avant commit : '+str(blocking))
                    if any(r['ecart_bronze_silver'] or r['ecart_silver_gold'] for r in conserved):
                        raise AssertionError('Conservation avant commit')
                    for m in measured:
                        cx.execute(text(f'''INSERT INTO {s5.table(dq,'dq_history')}(batch_id,couche,rule_id,table_cible,nb_testees,nb_echecs)
                          VALUES(:b,'GOLD',:r,:t,:n,:e)'''),{'b':batch,'r':m['rule_id'],'t':'S4R19_'+m['table_logique'],'n':m['nb_testees'],'e':m['nb_echecs']})
                if fail_at=='after_audit':raise RuntimeError('Panne injectée after_audit')
                return {'rejeu':False,'etat':params['e'],'empreintes':after,'reference':before,'bilan':bilan}
        finally:
            cx.execute(text("SELECT RELEASE_LOCK('s4_construction')"));cx.commit()


def historical_audit(cx,root):
    """Compare aux SHA S4 publiés, avec leur sérialisation et leurs colonnes exactes."""
    import pandas as pd
    expected=json.loads((Path(root)/'reports/S4_correctifs_synthese.json').read_text())['empreintes']
    result={}
    for name,wanted in expected.items():
        if name=='dq.rejets':
            query='SELECT batch_id,entite,source_systeme,bronze_row_id,rule_id,porte,motif FROM dq.rejets WHERE batch_id=:b'
        else:
            query='SELECT * FROM '+name+(' WHERE _batch_id=:b' if name!='gold.xref_identifiants' else '')
        df=pd.read_sql(text(query),cx,params={'b':BATCH},coerce_float=False)
        df=df.drop(columns=[c for c in ('silver_row_id','_processed_at') if c in df])
        payload=[json.dumps(list(r),ensure_ascii=False,default=str,separators=(',',':'))
                 for r in df.astype(object).where(df.notna(),None).itertuples(index=False,name=None)]
        actual={'n':len(df),'sha256':hashlib.sha256(json.dumps({'colonnes':list(df.columns),'lignes':sorted(payload)},ensure_ascii=False,separators=(',',':')).encode()).hexdigest()}
        if actual!=wanted:raise ValueError('Référence historique inattendue : '+name)
        result[name]=actual
    return result


def protected_fingerprints(cx):
    """Instantané multiensemble typé complet, y compris métadonnées et référentiels."""
    tables=[(origin,t) for origin,t,_ in __import__('s5_mesures').SOURCES]
    tables += [('bronze',t) for t in s5.BRONZE_TABLES]
    tables += [('silver',t) for t in ('client','contrat','sinistre','ref_ban','ref_postal','ref_pays')]
    results={}
    for schema,t in tables:
        data=_read(cx,schema,t)
        payloads=sorted(s5.json_bytes([s5.canonical(v) for v in r.values()]) for r in data)
        h=hashlib.sha256()
        for value in payloads:h.update(len(value).to_bytes(8,'big'));h.update(value)
        results[schema+'.'+t]={'n':len(data),'sha256':h.hexdigest()}
    return results


def checks(cx,clients,batch=BATCH):
    import s5_mesures
    g=_read(cx,'gold','client_unique');x=_read(cx,'gold','xref_identifiants')
    measurements=signature_summary(clients,x,g)
    queries={
      ('RQ-002','contrat'):"""SELECT COUNT(*) n,COALESCE(SUM(g.cli_id IS NULL OR g.nature_personne IS NULL
       OR g.nature_personne<>'PP' OR g.date_naissance IS NULL OR c.date_debut IS NULL
       OR TIMESTAMPDIFF(YEAR,g.date_naissance,c.date_debut)<18),0) ko
       FROM gold.contrat_certifie c LEFT JOIN gold.client_unique g
       ON g.cli_id=c.cli_souscripteur AND g._batch_id=c._batch_id
       WHERE c._batch_id=:b AND (g.nature_personne IS NULL OR g.nature_personne<>'PM')""",
      ('RQ-011','contrat'):'''SELECT COUNT(*) n,COALESCE(SUM(t.code_type IS NULL),0) ko FROM gold.contrat_certifie c
       LEFT JOIN bronze.crm_type_contrat t ON t.code_type=c.code_type AND t._batch_id=c._batch_id WHERE c._batch_id=:b''',
      ('RQ-012','contrat'):'''SELECT COUNT(*) n,COALESCE(SUM(g.cli_id IS NULL),0) ko FROM gold.contrat_certifie c
       LEFT JOIN gold.client_unique g ON g.cli_id=c.cli_souscripteur AND g._batch_id=c._batch_id WHERE c._batch_id=:b''',
      ('RQ-013','contrat'):'''SELECT COUNT(*) n,COALESCE(SUM(g.cli_id IS NULL),0) ko FROM gold.contrat_certifie c
       LEFT JOIN gold.client_unique g ON g.cli_id=c.cli_assure AND g._batch_id=c._batch_id WHERE c._batch_id=:b AND c.cli_assure IS NOT NULL''',
      ('RQ-017','sinistre_relation'):'''SELECT COUNT(*) n,COALESCE(SUM(c.contrat_id IS NULL),0) ko FROM gold.sinistre_certifie s
       LEFT JOIN gold.contrat_certifie c ON c.contrat_id=s.contrat_id AND c._batch_id=s._batch_id WHERE s._batch_id=:b''',
      ('RQ-017','sinistre_garantie'):'''SELECT COUNT(*) n,COALESCE(SUM(NOT EXISTS(SELECT 1 FROM gold.contrat_certifie d
        WHERE d._batch_id=s._batch_id AND d.cli_souscripteur=c.cli_souscripteur AND d.code_type=c.code_type
        AND s.date_survenance BETWEEN d.date_debut AND d.date_fin)),0) ko FROM gold.sinistre_certifie s
        LEFT JOIN gold.contrat_certifie c ON c.contrat_id=s.contrat_id AND c._batch_id=s._batch_id WHERE s._batch_id=:b''',
      ('RQ-015','client_unique'):'''SELECT COUNT(*) n,COALESCE(SUM(EXISTS(SELECT 1 FROM gold.contrat_certifie c
        WHERE c.cli_souscripteur=g.cli_id AND c._batch_id=g._batch_id)),0) ko FROM gold.client_unique g WHERE g._batch_id=:b AND g.statut_client='PROSPECT' ''',
      ('RQ-016','client_unique'):'''SELECT COUNT(*) n,COALESCE(SUM(NOT EXISTS(SELECT 1 FROM gold.contrat_certifie c
        WHERE c.cli_souscripteur=g.cli_id AND c._batch_id=g._batch_id)),0) ko FROM gold.client_unique g WHERE g._batch_id=:b AND g.statut_client IN ('ACTIF','INACTIF','A_REVOIR')''',
      ('RQ-018','v_client_actif'):'''SELECT COUNT(*) n,COALESCE(SUM((g.statut_client='ACTIF') <> EXISTS(SELECT 1 FROM gold.v_client_actif a
        WHERE a.cli_id=g.cli_id AND a._batch_id=g._batch_id)),0) ko FROM gold.client_unique g WHERE g._batch_id=:b''',
      ('RQ-001','contrat'):'''SELECT COUNT(*) n,COALESCE(SUM(date_fin IS NULL OR date_debut IS NULL OR date_fin<=date_debut),0) ko FROM gold.contrat_certifie WHERE _batch_id=:b''',
      ('RQ-010','contrat'):'''SELECT COUNT(*) n,COALESCE(SUM(duree_garantie_mois IS NULL OR duree_garantie_mois NOT IN (12,24,36,60)),0) ko FROM gold.contrat_certifie WHERE _batch_id=:b''',
    }
    for scope,query in s5_mesures.lineage_queries(quarantine_dq='dq').items():queries[('RQ-023',scope)]=query
    for (rule,scope),query in queries.items():
        row=cx.execute(text(query),{'b':batch}).mappings().one()
        n,ko=int(row['n']),int(row['ko'])
        measurements.append({'rule_id':rule,'table_logique':scope,'nb_testees':n,'nb_echecs':ko,
                             'requete':query,'taux':100*(n-ko)/n if n else None,
                             'exclusions_rq019_justifiees':int(row.get('exclusions_rq019',0))})
    conservation=[]
    for entity,origin,bt,st,gt in [('client','crm','crm_client','client','xref_identifiants'),
                                ('client','cif','cif_clients','client','xref_identifiants'),
                                ('contrat','crm','crm_contrat','contrat','contrat_certifie'),
                                ('sinistre','crm','crm_sinistre','sinistre','sinistre_certifie')]:
        p={'b':batch,'e':entity,'o':origin}
        nbronze=cx.execute(text(f'SELECT COUNT(*) FROM bronze.{bt} WHERE _batch_id=:b'),p).scalar_one()
        nsilver=cx.execute(text(f'SELECT COUNT(*) FROM silver.{st} WHERE _batch_id=:b'+(' AND source_systeme=:o' if entity=='client' else '')),p).scalar_one()
        ngold=cx.execute(text(f'SELECT COUNT(*) FROM gold.{gt}'+(' WHERE source_systeme=:o' if entity=='client' else ' WHERE _batch_id=:b')),p).scalar_one()
        counts={gate:cx.execute(text('''SELECT COUNT(DISTINCT bronze_row_id) FROM dq.rejets WHERE batch_id=:b
           AND entite=:e AND source_systeme=:o AND porte=:gate'''),dict(p,gate=gate)).scalar_one() for gate in ('S','G')}
        row={'entite':entity,'origine':origin,'bronze':nbronze,'silver':nsilver,'retenues_gold_sources':ngold,
             'rejets_S_distincts':counts['S'],'rejets_G_distincts':counts['G'],
             'ecart_bronze_silver':nbronze-nsilver-counts['S'],'ecart_silver_gold':nsilver-ngold-counts['G']}
        conservation.append(row)
    return measurements,conservation


def run(root='/home/jovyan/work',engine=None,tests=None):
    """Point d'entrée unique de la section autonome du notebook S4."""
    from sqlalchemy import create_engine
    from datetime import datetime,timezone
    engine=engine or create_engine('mysql+pymysql://root:root@mariadb:3306')
    root=Path(root)
    labelpath=root/'data/referentiels/paires_etiquetees.csv'
    if hashlib.sha256(labelpath.read_bytes()).hexdigest()!=LABEL_SHA:raise ValueError('Labels modifiés')
    labels=list(csv.DictReader(labelpath.open()))
    with engine.connect() as cx:
        exists=cx.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='dq' AND table_name='rq019_etat'")).scalar_one()
        state=_read(cx,'dq','rq019_etat') if exists else []
        protected_before=protected_fingerprints(cx)
        historical=historical_audit(cx,root) if not state else {'reference_verifiee_a_la_premiere_application':True}
        clients=_read(cx,'silver','client')
        reference={t:_read(cx,'dq','rq019_reference_'+t) if state else _read(cx,'gold',t) for t in TABLES}
        before=signature_summary(clients,reference['xref_identifiants'],reference['client_unique'])
        # Le plan réellement appliqué reste immuable ; un changement de politique
        # exige restauration et nouvelle procédure, pas une substitution silencieuse.
        plan=json.loads(state[0]['plan_json']) if state else build_plan(clients,reference['xref_identifiants'],reference['client_unique'],labels)
    outcome=apply(engine,plan)
    replay=apply(engine,plan)
    if outcome['empreintes']!=replay['empreintes']:raise AssertionError('Rejeu différent')
    with engine.begin() as cx:
        protected_after=protected_fingerprints(cx)
        if protected_before!=protected_after:raise AssertionError('Données protégées modifiées')
        measurements,conservation=checks(cx,clients)
        if any(m['nb_echecs'] for m in measurements if m['rule_id']=='RQ-019'):raise AssertionError('Collision RQ019 retenue')
        if any(r['ecart_bronze_silver'] or r['ecart_silver_gold'] for r in conservation):raise AssertionError('Conservation')
        manifest=_read(cx,'dq','s4_manifeste')
        after_gold=_read(cx,'gold','client_unique');after_xref=_read(cx,'gold','xref_identifiants')
        # Traces qualifiées sans afficher de valeurs personnelles supplémentaires.
        traces=[]
        for name,condition in [('Meunier',lambda r:(r['source_systeme'],r['source_id']) in {('crm','A-4471'),('crm','H-9012'),('crm','S-2208'),('cif','K471226')}),
                               ('CP_zero_initial',lambda r:r['source_systeme']=='crm' and r['source_id']=='A-10062')]:
            selected=[r for r in clients if condition(r)]
            if name=='CP_zero_initial':selected=selected[:1]
            ids={r['silver_row_id'] for r in selected};retained=[x for x in after_xref if x['silver_row_id'] in ids]
            traces.append({'trace':name,'sources':len(selected),'sources_retenues':len(retained),
                           'cli_retenus':sorted({x['cli_id'] for x in retained}),
                           'sources_quarantaine':len(selected)-len(retained),
                           'requete':'silver.client -> gold.xref_identifiants par source_systeme + bronze_row_id + silver_row_id + source_id'})
        address=cx.execute(text('''SELECT s.sinistre_id,s.bronze_row_id,s.silver_row_id,(g.sinistre_id IS NOT NULL) AS retenu_gold FROM silver.sinistre s
           LEFT JOIN gold.sinistre_certifie g ON g.sinistre_id=s.sinistre_id AND g._batch_id=s._batch_id
           WHERE s._batch_id=:b AND s.sinistre_id='SIN0000008' LIMIT 1'''),{'b':BATCH}).mappings().first()
        traces.append({'trace':'adresse_sinistre','reference':dict(address) if address else None,
                       'preuve':'attributs gold copiés exactement de référence ; empreintes et lineage remesurés'})
    report={'batch_id':BATCH,'date_execution':datetime.now(timezone.utc).isoformat(),
      'configuration_avant':BASE_CONFIG,
      'configuration_apres':json.loads((root/'reports/S4_RQ019_resolution.json').read_text())['configuration_apres'] if state and (root/'reports/S4_RQ019_resolution.json').exists() else ({'empreinte_appliquee':plan['configuration_sha256'],'description':'Plan historique complet conservé dans dq.rq019_etat.plan_json ; configuration du vérificateur distincte.'} if state else CONFIG),
      'configuration_code_verification':CONFIG,
      'configuration_sha256':plan['configuration_sha256'],
      'code_verification_courant_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'instruction_utilisateur':'Appliquer les critères techniques, mettre les incertitudes en quarantaine ; aucune approbation Owner',
      'statut':'GOLD_CANDIDAT_NON_ACCEPTE','manifeste':manifest,'audit_reference':historical,
      'labels':{'sha256':LABEL_SHA,'nombre':len(labels),'positifs':sum(r['meme_personne']=='1' for r in labels)},
      'plan':{**{k:v for k,v in plan.items() if k not in ('mapping','source_roles')},
        'mapping_modifie':{k:v for k,v in plan['mapping'].items() if k!=v},
        'plan_complet':'dq.rq019_etat.plan_json ; mappings identiques omis dans ce rapport'},'application':outcome,'rejeu':replay,'avant_rq019':before,'mesures_apres':measurements,
      'conservation':conservation,'proteges_avant':protected_before,'proteges_apres':protected_after,
      'nonmutation_proteges':protected_before==protected_after,'tests':tests,'traces':traces,
      'preuves_s5_anterieures':'PÉRIMÉES pour le nouveau gold : ancienne configuration/empreinte. Rapports et certificat historiques conservés.',
      'limites':['Consolidations selon critères techniques S4, sans confirmation humaine d’identité.',
       'La quarantaine réduit le périmètre candidat ; aucun taux de conformité source déduit.',
       'Refus Owner historique conservé ; aucune attestation exhaustive ni publication nominale.',
       'Les autres règles client de format/complétude ne sont pas toutes remesurées par ce traitement ; aucun GO exhaustif.']}
    target=root/'reports/S4_RQ019_resolution.json'
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n')
    return report


def _validate_target(target,rejects,reference):
    clients={r['cli_id'] for r in target['client_unique']}
    contracts={r['contrat_id'] for r in target['contrat_certifie']}
    if any(x['cli_id'] not in clients for x in target['xref_identifiants']):raise AssertionError('Orphelin xref')
    if any(c['cli_souscripteur'] not in clients or (c['cli_assure'] is not None and c['cli_assure'] not in clients) for c in target['contrat_certifie']):raise AssertionError('Orphelin contrat')
    if any(s['contrat_id'] not in contracts for s in target['sinistre_certifie']):raise AssertionError('Orphelin sinistre')
    for entity,table in [('client','xref_identifiants'),('contrat','contrat_certifie'),('sinistre','sinistre_certifie')]:
        removed={(r.get('source_systeme','crm'),r['bronze_row_id']) for r in rejects if r['entite']==entity}
        kept={(r.get('source_systeme','crm'),r['bronze_row_id']) for r in target[table]}
        baseline={(r.get('source_systeme','crm'),r['bronze_row_id']) for r in reference[table]}
        if kept & removed or kept | removed != baseline:raise AssertionError('Conservation cible '+entity)

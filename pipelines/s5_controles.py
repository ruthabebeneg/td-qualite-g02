"""Exécuteur S5 B/S/G : mesures réellement recalculées, liées au snapshot.

Aucun effet à l'import. Seul dq.dq_history est écrit. Le résultat n'est ni une
approbation métier, ni un certificat, ni une autorisation de publication.
"""
from datetime import date, datetime, timezone
import calendar
import hashlib
import re
import unicodedata
from sqlalchemy import text
import s5_engineering as s5
import s5_mesures as measures
import s4_rq019 as rq


def norm(value):
    if value is None:
        return None
    return ' '.join(unicodedata.normalize('NFKD',str(value)).encode('ascii','ignore').decode().upper().split())


def _add(out,layer,rule,scope,n,ko,population,**evidence):
    n,ko=int(n),int(ko)
    if not 0<=ko<=n:
        raise ValueError('Effectifs invalides : '+rule+'/'+scope)
    out[(layer,rule,scope)]={'couche':layer,'rule_id':rule,'table_logique':scope,
        'nb_testees':n,'nb_echecs':ko,'population':population,
        'taux':100*(n-ko)/n if n else None,**evidence}


def _query(cx,out,layer,rule,scope,sql,batch,population):
    row=cx.execute(text(sql),{'b':batch}).mappings().one()
    _add(out,layer,rule,scope,row['n'],row['ko'],population,requete=sql)


def bronze_controls(cx,batch,out):
    for origin,source,target in measures.SOURCES:
        names=[c['name'] for c in s5.columns(cx,origin,source)]
        src,source_set=measures._signature(measures._business(cx,origin,source,names))
        br,bronze_set=measures._signature(measures._business(cx,'bronze',target,names,batch))
        ok=src==br and source_set==bronze_set
        _add(out,'BRONZE','RQ-021',target,1,int(not ok),
             'Un contrôle global par table : effectif, somme CRC32, SHA256 et multiensemble exact après CAST CHAR.',
             source=src,bronze=br,contenu_exact_identique=ok)
        data=measures._business(cx,'bronze',target,names+['_batch_id','_source_system','_ingested_at','_row_hash'],batch)
        failures=0
        for row in data:
            business,meta=row[:-4],row[-4:]
            failures+=int(any(v is None or not v.strip() for v in meta)
                or meta[0]!=batch or meta[1]!=origin
                or meta[3]!=hashlib.sha256(measures._payload(business)).hexdigest()[:16])
        _add(out,'BRONZE','RQ-022',target,len(data),failures,
             'Chaque ligne du lot : lot/source/horodatage/hash présents ; hash métier revalidé comme S1.')


def _keys(cx,out,layer,schema,table,scope,key,batch,extra=''):
    field=s5.ident(key)
    sql=f'''SELECT COUNT(*) n,COALESCE(SUM(k IS NULL OR TRIM(CAST(k AS CHAR))='' OR multiplicite>1),0) ko
      FROM (SELECT {field} k,COUNT(*) OVER(PARTITION BY {field}) multiplicite
       FROM {s5.table(schema,table)} WHERE _batch_id=:b {extra}) d'''
    _query(cx,out,layer,'RQ-020',scope,sql,batch,'Toutes les lignes du lot/périmètre ; clé métier NULL/vide ou dupliquée en échec.')


def client_controls(cx,batch,out):
    postal={(str(r['code_postal']),norm(r['commune'])) for r in s5.rows(cx,'SELECT code_postal,commune FROM silver.ref_postal')}
    countries={r['code_pays'] for r in s5.rows(cx,'SELECT code_pays FROM silver.ref_pays')}
    for layer,schema,table,scope,where in [
        ('SILVER','silver','client','client_crm'," AND source_systeme='crm'"),
        ('SILVER','silver','client','client_cif'," AND source_systeme='cif'"),
        ('GOLD','gold','client_unique','client_unique','')]:
        data=s5.rows(cx,f'SELECT * FROM {s5.table(schema,table)} WHERE _batch_id=:b'+where,{'b':batch})
        gold=layer=='GOLD'
        vals={rule:[0,0] for rule in ['RQ-003','RQ-004','RQ-005','RQ-006','RQ-007','RQ-008']}
        if scope!='client_cif':vals['RQ-009']=[0,0]
        for r in data:
            country=r['pays_iso'];cp=r['cp'];town=r['ville'] if gold else r['ville_normalisee']
            tel=r['telephone'] if gold else r['telephone_normalise'];mail=r['email'] if gold else r['email_normalise']
            subscriber=r['statut_client'] in ('ACTIF','INACTIF','A_REVOIR') if gold else r['type_personne']=='souscripteur'
            checks={'RQ-007':(True,country in countries),
                'RQ-003':(scope!='client_cif' and subscriber,tel is not None and bool(str(tel).strip())),
                'RQ-004':(country=='FR' and tel is not None,bool(re.fullmatch(r'0[1-9]\d{8}',str(tel)))),
                'RQ-005':(country=='FR',bool(re.fullmatch(r'\d{5}',str(cp)))),
                'RQ-006':(country=='FR',(str(cp),norm(town)) in postal),
                'RQ-008':(mail is not None,bool(re.fullmatch(r'[^@\s]+@[^@\s]+\.[a-z]{2,}',str(mail))))}
            if scope!='client_cif':
                checks['RQ-009']=(True,r['statut_client'] in ('ACTIF','INACTIF','A_REVOIR','ASSURE','PROSPECT') if gold
                                  else r['type_personne'] in ('prospect','souscripteur','assure'))
            for rule,(applicable,ok) in checks.items():
                vals[rule][0]+=int(applicable);vals[rule][1]+=int(applicable and not ok)
        for rule,(n,e) in vals.items():
            # CIF sans rôle : aucune population de souscripteurs déclarée ni conformité fictive.
            if rule=='RQ-003' and scope=='client_cif':continue
            _add(out,layer,rule,scope,n,e,
                 'Souscripteurs uniquement pour RQ003 ; France pour RQ004/005/006 ; contacts renseignés pour RQ004/008 ; pays/domaine sur toutes les lignes.',
                 exclusions=len(data)-n,non_applicabilite='Population applicable vide, ne vaut pas 100 %.' if n==0 else None)
        _keys(cx,out,layer,schema,table,scope,'cli_id' if gold else 'source_id',batch,where)


def silver_controls(cx,batch,out):
    for rule,predicate in [('RQ-001','date_fin IS NULL OR date_debut IS NULL OR date_fin<=date_debut'),
                           ('RQ-010','duree_garantie_mois IS NULL OR duree_garantie_mois NOT IN (12,24,36,60)')]:
        _query(cx,out,'SILVER',rule,'contrat',f'SELECT COUNT(*) n,COALESCE(SUM({predicate}),0) ko FROM silver.contrat WHERE _batch_id=:b',batch,
               'Tous contrats silver du lot ; valeurs NULL en échec.')
    for entity in ('contrat','sinistre'):_keys(cx,out,'SILVER','silver',entity,entity,entity+'_id',batch)
    for origin,t,bt,pk,scope,extra in [
        ('crm','client','crm_client','client_id','client_crm'," AND s.source_systeme='crm'"),
        ('cif','client','cif_clients','column0','client_cif'," AND s.source_systeme='cif'"),
        ('crm','contrat','crm_contrat','contrat_id','contrat_crm',''),
        ('crm','sinistre','crm_sinistre','sinistre_id','sinistre_crm','')]:
        sk='source_id' if t=='client' else pk
        sql=f'''SELECT COUNT(*) n,COALESCE(SUM(b.bronze_row_id IS NULL),0) ko
          FROM silver.{t} s LEFT JOIN bronze.{bt} b ON b.bronze_row_id=s.bronze_row_id
          AND b._batch_id=s._batch_id AND b.{pk}=s.{sk} WHERE s._batch_id=:b {extra}'''
        _query(cx,out,'SILVER','RQ-023',scope,sql,batch,'Toutes lignes silver, origine/lot/clé/bronze_row_id qualifiés ; LEFT JOIN.')
        nbronze=cx.execute(text(f'SELECT COUNT(*) FROM bronze.{bt} WHERE _batch_id=:b'),{'b':batch}).scalar_one()
        nstored=cx.execute(text(f'SELECT COUNT(*) FROM silver.{t} s WHERE _batch_id=:b {extra}'),{'b':batch}).scalar_one()
        nr=cx.execute(text('''SELECT COUNT(DISTINCT bronze_row_id) FROM dq.rejets WHERE batch_id=:b
           AND entite=:e AND source_systeme=:o AND porte='S' '''),{'b':batch,'e':t,'o':origin}).scalar_one()
        overlap=cx.execute(text(f'''SELECT COUNT(*) FROM silver.{t} s WHERE s._batch_id=:b {extra}
          AND EXISTS(SELECT 1 FROM dq.rejets r WHERE r.batch_id=s._batch_id AND r.entite=:e
            AND r.source_systeme=:o AND r.bronze_row_id=s.bronze_row_id AND r.porte='S')'''),
            {'b':batch,'e':t,'o':origin}).scalar_one()
        invalid_rejects=cx.execute(text(f'''SELECT COUNT(DISTINCT r.bronze_row_id) FROM dq.rejets r
          LEFT JOIN bronze.{bt} b ON b.bronze_row_id=r.bronze_row_id AND b._batch_id=r.batch_id
          WHERE r.batch_id=:b AND r.entite=:e AND r.source_systeme=:o AND r.porte='S'
            AND b.bronze_row_id IS NULL'''),{'b':batch,'e':t,'o':origin}).scalar_one()
        _add(out,'SILVER','RQ-024',f'{t} ({origin})',1,int(nstored+nr!=nbronze or overlap>0 or invalid_rejects>0),
             'Un contrôle global par table/origine : silver + rejets S distincts = bronze ; ensembles disjoints, références de rejets valides.',
             bronze=int(nbronze),silver=int(nstored),rejets_distincts=int(nr),chevauchement=int(overlap),rejets_sans_bronze=int(invalid_rejects))


def ban_controls(cx,batch,out):
    reference={r['id_ban']:r for r in s5.rows(cx,'SELECT * FROM silver.ref_ban')}
    for layer,schema,table in [('SILVER','silver','sinistre'),('GOLD','gold','sinistre_certifie')]:
        data=s5.rows(cx,f'SELECT * FROM {s5.table(schema,table)} WHERE _batch_id=:b',{'b':batch})
        bad=0
        for r in data:
            b=reference.get(r['id_ban'])
            ok=bool(b and r['cp_sinistre']==b['code_postal']
                    and norm(r['ville_sinistre'])==norm(b['commune'])
                    and norm(r['adresse_sinistre'])==norm(str(b['numero'])+' '+b['voie']))
            bad+=int(not ok)
        _add(out,layer,'RQ-014','sinistre',len(data),bad,
             'Tous sinistres retenus : id BAN existant, CP/commune/adresse concordants au référentiel, normalisation accents/casse/espaces ; NULL en échec.')
        if layer=='GOLD':_keys(cx,out,layer,schema,table,'sinistre','sinistre_id',batch)


def active_controls(cx,batch,out):
    """Trois lectures SQL, un calcul Python indépendant et la vue existante."""
    ref=date.fromisoformat(batch.removeprefix('L-'))
    month_index=ref.year*12+ref.month-1-3
    year,month=divmod(month_index,12);month+=1
    minimum=date(year,month,min(ref.day,calendar.monthrange(year,month)[1]))
    sql="""SELECT COUNT(DISTINCT cli_souscripteur) FROM gold.contrat_certifie
      WHERE _batch_id=:b AND date_debut<=:reference AND date_fin>=:reference
        AND date_derniere_cotisation>=:minimum"""
    counts={direction:int(cx.execute(text(sql),{'b':batch,'reference':ref,'minimum':minimum}).scalar_one())
            for direction in ('Commerciale','Sinistres','Risques')}
    contracts=s5.rows(cx,'SELECT cli_souscripteur,date_debut,date_fin,date_derniere_cotisation FROM gold.contrat_certifie WHERE _batch_id=:b',{'b':batch})
    python_active={r['cli_souscripteur'] for r in contracts if r['cli_souscripteur'] is not None
        and r['date_debut'] is not None and r['date_fin'] is not None
        and r['date_derniere_cotisation'] is not None
        and r['date_debut']<=ref<=r['date_fin'] and r['date_derniere_cotisation']>=minimum}
    view_active={r['cli_id'] for r in s5.rows(cx,'SELECT cli_id FROM gold.v_client_actif WHERE _batch_id=:b',{'b':batch})}
    failures=sum(n!=len(python_active) or view_active!=python_active for n in counts.values())
    _add(out,'GOLD','RQ-018','v_client_actif',3,failures,
         'Trois comptages SQL de la définition CD-001, comparés à Python indépendant et aux identités de la vue ; cotisation NULL non à jour.',
         requete=sql,date_reference=ref.isoformat(),cotisation_min=minimum.isoformat(),
         comptages_directions=counts,actifs_python=len(python_active),actifs_vue=len(view_active),
         ecart_identites_vue_python=len(view_active.symmetric_difference(python_active)))


def collect(cx,batch):
    """Lecture des contenus actuels ; ne lit aucun taux historique comme résultat."""
    out={}
    bronze_controls(cx,batch,out)
    client_controls(cx,batch,out)
    silver_controls(cx,batch,out)
    ban_controls(cx,batch,out)
    clients=s5.rows(cx,'SELECT * FROM silver.client WHERE _batch_id=:b',{'b':batch})
    gold,conservation=rq.checks(cx,clients,batch)
    for m in gold:
        # Conserver le contrôle des statuts : la concordance des trois lectures
        # et de la vue ne prouve pas que statut_client a été correctement calculé.
        scope='statut_client_actif' if m['rule_id']=='RQ-018' and m['table_logique']=='v_client_actif' else m['table_logique']
        _add(out,'GOLD',m['rule_id'],scope,m['nb_testees'],m['nb_echecs'],
             m.get('population','Contrôle gold recalculé ; définition et SQL conservés.'),
             **{k:v for k,v in m.items() if k not in ('rule_id','table_logique','nb_testees','nb_echecs','population','taux')})
    _keys(cx,out,'GOLD','gold','contrat_certifie','contrat','contrat_id',batch)
    active_controls(cx,batch,out)
    return list(out.values()),conservation


def expected_scopes(cx,batch,layout,catalogue):
    history=s5._history(cx,batch,layout)
    expected=s5.required_scopes(catalogue,synthetic=layout.synthetic)
    known={(m['couche'],m['rule_id'],m['table_logique']) for m in expected}
    for m in s5._coverage(history,catalogue,layout):
        k=(m['couche'],m['rule_id'],m['table_logique'])
        if k not in known:
            rule=next(r for r in catalogue if r['rule_id']==m['rule_id'])
            expected.append({'rule_id':m['rule_id'],'couche':m['couche'],
                'table_logique':m['table_logique'],'seuil_min':str(rule['seuil_min'])})
            known.add(k)
    return expected


def _assert_single_batch(cx,batch):
    """Le socle S4 est mono-lot ; refuser au lieu de mélanger deux instantanés."""
    for schema,tables in [('bronze',s5.BRONZE_TABLES),
                          ('silver',('client','contrat','sinistre')),
                          ('gold',('client_unique','contrat_certifie','sinistre_certifie'))]:
        for table in tables:
            other=cx.execute(text(f'SELECT COUNT(*) FROM {s5.table(schema,table)} WHERE _batch_id IS NULL OR _batch_id<>:b'),{'b':batch}).scalar_one()
            if other:
                raise ValueError('Contrôles mono-lot : lignes étrangères dans '+schema+'.'+table)


def _validate_conservation(calculated,conservation):
    """La liaison de contrôles n'est pas émise sur une conservation incohérente."""
    if not conservation:
        raise ValueError('Bilan de conservation absent')
    for row in conservation:
        if not {'ecart_bronze_silver','ecart_silver_gold'} <= row.keys():
            raise ValueError('Bilan de conservation incomplet')
    for row in list(conservation)+list(calculated):
        for key,value in row.items():
            if key in ('ecart_bronze_silver','ecart_silver_gold','chevauchement','rejets_sans_bronze'):
                if value != 0:
                    raise ValueError('Conservation invalide : '+key+'='+str(value))


def _persist_and_attest(cx,batch,layout,calculated,conservation,content_before):
    """Appelé dans la transaction du demandeur ; toute erreur doit remonter.

    Les mesures, leur historique et la liaison au contenu sont validés ensemble.
    Le layout rend cette frontière transactionnelle testable sur schémas isolés.
    """
    _validate_conservation(calculated,conservation)
    catalogue=s5._catalogue(cx,layout)
    bykey={(m['couche'],m['rule_id'],m['table_logique']):m for m in calculated}
    if len(bykey)!=len(calculated):
        raise ValueError('Périmètres de mesure dupliqués')
    for m in calculated:
        if not 0 <= m['nb_echecs'] <= m['nb_testees']:
            raise ValueError('Effectifs impossibles')
    expected=expected_scopes(cx,batch,layout,catalogue)
    missing=[x for x in expected if (x['couche'],x['rule_id'],x['table_logique']) not in bykey]
    if missing:raise ValueError('Contrôles non implémentés : '+str(missing))
    for m in calculated:
        cx.execute(text(f'''INSERT INTO {s5.table(layout.dq,'dq_history')}
          (batch_id,couche,rule_id,table_cible,nb_testees,nb_echecs)
          VALUES(:b,:c,:r,:t,:n,:e)'''),{'b':batch,'c':m['couche'],'r':m['rule_id'],
          't':'S5_'+m['table_logique'],'n':m['nb_testees'],'e':m['nb_echecs']})
    expected=expected_scopes(cx,batch,layout,catalogue)
    history=s5._history(cx,batch,layout);manifest=s5._manifest(cx,batch,layout)
    content_after=s5.control_content(cx,layout)
    if content_before!=content_after:raise ValueError('Contenu changé pendant les contrôles')
    attestation={'synthetique':layout.synthetic,'batch_id':batch,'schema_gold':layout.gold,'schema_dq':layout.dq,
        'gold_sha256':s5.fingerprint_gold(cx,batch,layout)['sha256'],
        'history_sha256':history['sha256'],'configuration':manifest,
        'catalogue_sha256':s5.digest(catalogue),'politique_sha256':s5.policy_fingerprint(catalogue,layout),
        'contenu_controles_sha256':content_after,'scopes_sha256':s5.digest(expected),
        'mesures_executees':[{'scope':scope,'nb_testees':bykey[(scope['couche'],scope['rule_id'],scope['table_logique'])]['nb_testees'],
            'nb_echecs':bykey[(scope['couche'],scope['rule_id'],scope['table_logique'])]['nb_echecs']} for scope in expected],
        'execute_le':datetime.now(timezone.utc).isoformat()}
    if not s5.attestation_valid(cx,attestation,batch,layout,s5.fingerprint_gold(cx,batch,layout),history,catalogue,manifest):
        raise AssertionError('Liaison des contrôles invalide')
    return {'attestation':attestation,'mesures':calculated,'conservation':conservation,
            'nombre_controles':len(calculated),'perimetres_bloquants_attestes':len(expected),
            'historique_anterieur_preserve':True,'publication':False}


def run(engine,batch):
    """Mesure, historise et lie les résultats dans le même snapshot transactionnel."""
    layout=s5.Layout()
    with s5.coherent_connection(engine) as cx:
        s5.assert_transactional(cx,layout)
        _assert_single_batch(cx,batch)
        content_before=s5.control_content(cx,layout)
        calculated,conservation=collect(cx,batch)
        return _persist_and_attest(cx,batch,layout,calculated,conservation,content_before)

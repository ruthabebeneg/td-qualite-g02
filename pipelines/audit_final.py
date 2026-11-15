"""Vérifications en lecture seule du rendu corrigé, sans changer les certificats."""
from pathlib import Path
import json

import s5_engineering as s5


def repository_root(start=None):
    start = Path(start or Path.cwd()).resolve()
    for candidate in (start, *start.parents):
        if (candidate / 'pipelines/s5_engineering.py').is_file():
            return candidate
    raise FileNotFoundError('Racine du dépôt introuvable')


def reference_state(cx, batch, certificate, layout=s5.Layout()):
    """Des volumes égaux ne suffisent jamais à reconnaître la référence."""
    gold = s5.fingerprint_gold(cx, batch, layout)
    history = s5._history(cx, batch, layout)
    manifest = s5._manifest(cx, batch, layout)
    catalogue = s5._catalogue(cx, layout)
    same = (certificate.get('batch_id') == batch
            and certificate.get('gold') == gold
            and certificate.get('history_sha256') == history['sha256']
            and s5.digest(certificate.get('manifeste')) == s5.digest(manifest)
            and certificate.get('catalogue_sha256') == s5.digest(catalogue)
            and certificate.get('politique_sha256') == s5.policy_fingerprint(catalogue, layout))
    return {'identique': same, 'gold': gold, 'historique': history, 'manifeste': manifest}


def published_state(engine, batch, certificate, layout=s5.Layout()):
    """Reconnaît un lot déjà publié et vérifie son contenu sans DELETE/INSERT.

    Une cible vide sans publication antérieure retourne None. Toute cible occupée doit être intégralement
    reliée au certificat GO et au journal, sinon le rejeu est refusé.
    """
    with s5.coherent_connection(engine) as cx:
        target = {}
        for _, dst in s5.MAPPING:
            if not s5.columns(cx, layout.target, dst):
                target[dst] = None
            else:
                target[dst] = s5.fingerprint_table(cx, layout.target, dst)
        if all(value is None or value['lignes'] == 0 for value in target.values()):
            prior = (s5.rows(cx, f"SELECT publication_id FROM {s5.table(layout.dq,'s5_publication')} WHERE batch_id=:b", {'b': batch})
                     if s5.columns(cx, layout.dq, 's5_publication') else [])
            if prior:
                raise s5.PublicationRefusee('CIBLE_PUBLIEE_VIDE')
            return None
        state = reference_state(cx, batch, certificate, layout)
        if certificate.get('decision') != 'GO' or not state['identique']:
            raise s5.PublicationRefusee('CIBLE_EXISTANTE_REFERENCE_DIFFERENTE')
        cid = certificate['certificat_id']
        evidence = s5.rows(cx, f"SELECT preuve,preuve_sha256 FROM {s5.table(layout.dq,'s5_certification')} WHERE certificat_id=:c", {'c': cid})
        if len(evidence) != 1:
            raise s5.PublicationRefusee('PREUVE_CERTIFICAT_ABSENTE')
        proof = json.loads(evidence[0]['preuve'])
        if (s5.digest(proof) != evidence[0]['preuve_sha256'] or s5.digest(proof) != s5.digest({k: v for k, v in certificate.items() if k not in ('certificat_id', 'preuve_sha256')})
                or certificate.get('preuve_sha256') != evidence[0]['preuve_sha256']):
            raise s5.PublicationRefusee('PREUVE_CERTIFICAT_ALTEREE')
        certs = s5.rows(cx, f"SELECT decision,batch_id,empreinte_gold FROM {s5.table(layout.dq,'certificat_qualite')} WHERE certificat_id=:c", {'c': cid})
        if len(certs) != 1 or certs[0]['decision'] != 'GO' or certs[0]['batch_id'] != batch or certs[0]['empreinte_gold'] != state['gold']['sha256']:
            raise s5.PublicationRefusee('CERTIFICAT_PUBLIE_INCOMPATIBLE')
        if not s5.owner_valid(certificate['owner'], batch, state['manifeste'], state['gold']['sha256'], state['historique']['sha256']):
            raise s5.PublicationRefusee('VALIDATION_OWNER_PERIMEE')
        journal = s5.rows(cx, f"SELECT publication_id,batch_id,certificat_id,empreinte_gold,preuve FROM {s5.table(layout.dq,'s5_publication')} WHERE batch_id=:b AND certificat_id=:c ORDER BY publie_le,publication_id", {'b': batch, 'c': cid})
        if not journal or any(row['empreinte_gold'] != state['gold']['sha256'] for row in journal):
            raise s5.PublicationRefusee('JOURNAL_PUBLICATION_INCOMPATIBLE')
        reconciliation = []
        for src, dst in s5.MAPPING:
            expected = state['gold']['tables'][src]
            if target[dst] != expected:
                raise s5.PublicationRefusee('RQ025_ECART_CONTENU')
            reconciliation.append({'table_gold': src, 'table_cible': dst, 'gold': expected, 'cible': target[dst], 'ecart': 0})
        for row in journal:
            try:
                recorded = json.loads(row['preuve'])
                expected_links = {'batch_id': batch, 'certificat_id': cid,
                                  'empreinte_gold': state['gold']['sha256'],
                                  'publication_id': row['publication_id']}
                if (any(recorded.get(k) != v for k, v in expected_links.items())
                        or row.get('batch_id') != batch or row.get('certificat_id') != cid
                        or recorded.get('reconciliation') != reconciliation):
                    raise ValueError('Liens ou réconciliation incohérents')
            except (ValueError, TypeError, KeyError, AttributeError) as exc:
                raise s5.PublicationRefusee('PREUVE_PUBLICATION_ALTEREE') from exc
        if any(s5._integrity(cx, layout, batch, target=True).values()):
            raise s5.PublicationRefusee('CIBLE_ORPHELINE')
        return {'batch_id': batch, 'certificat_id': cid, 'publication': 'DEJA_PUBLIEE_VERIFIEE',
                'publication_id': journal[-1]['publication_id'], 'reconciliation': reconciliation,
                'ecritures': 0, 'journal_entrees': len(journal)}


def historical_steward_policy(export, certificate):
    """Vérifie toutes les lignes B/S/G, ordonnées par id avant dédoublonnage.

    Un export des seules dernières mesures ne constitue pas la preuve complète.
    Aucune ligne non empreintée ne peut être consommée par le notebook.
    """
    def refuse(reason):
        raise ValueError('REPLI_STEWARD_REFUSE : ' + reason)

    if not isinstance(export, dict) or not isinstance(certificate, dict):
        refuse('objet historique ou certificat malformé')
    catalogue = export.get('catalogue')
    fields = {'rule_id', 'libelle', 'dimension', 'porte', 'severite', 'seuil_min'}
    if (not isinstance(catalogue, list) or not catalogue
            or any(not isinstance(r, dict) or not fields.issubset(r) for r in catalogue)):
        refuse('catalogue historique complet absent ou malformé')
    for rule in catalogue:
        if any(not isinstance(rule[key], str) or not rule[key] for key in fields - {'seuil_min'}):
            refuse('valeurs du catalogue malformées')
        try:
            threshold = float(rule['seuil_min'])
        except (TypeError, ValueError):
            refuse('seuil du catalogue malformé')
        if not 0 <= threshold <= 100:
            refuse('seuil du catalogue hors domaine')
    if (export.get('batch_id') != certificate.get('batch_id')
            or s5.digest(catalogue) != certificate.get('catalogue_sha256')):
        refuse('catalogue historique non lié au certificat')
    history = export.get('historique')
    if not isinstance(history, dict) or not isinstance(history.get('mesures'), list) or not history['mesures']:
        refuse('historique absent ou malformé')
    measured = history['mesures']
    required = {'id', 'couche', 'rule_id', 'table_cible', 'nb_testees', 'nb_echecs'}
    for row in measured:
        if not isinstance(row, dict) or not required.issubset(row):
            refuse('mesure historique malformée')
        if row['couche'] not in ('BRONZE', 'SILVER', 'GOLD'):
            refuse('mesure hors périmètre B/S/G')
        if (not isinstance(row['id'], int) or isinstance(row['id'], bool)
                or any(not isinstance(row[k], int) or isinstance(row[k], bool) for k in ('nb_testees', 'nb_echecs'))
                or not 0 <= row['nb_echecs'] <= row['nb_testees']
                or not isinstance(row['table_cible'], str) or not isinstance(row['rule_id'], str)):
            refuse('valeurs de mesure malformées')
    if any(a['id'] >= b['id'] for a, b in zip(measured, measured[1:])):
        refuse('mesures historiques non ordonnées par id')
    if (history.get('sha256') != certificate.get('history_sha256')
            or s5.digest(measured) != certificate.get('history_sha256')):
        refuse('mesures historiques incomplètes ou altérées')
    return catalogue

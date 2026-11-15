"""Contre-exemple synthétique de survie, sans exécuter la construction S4."""
import ast
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def demonstrate():
    notebook = ROOT / 'notebooks/S4_g02.ipynb'
    cells = json.loads(notebook.read_text())['cells']
    function = next(node for cell in cells if cell['cell_type'] == 'code'
                    for node in ast.walk(ast.parse(''.join(cell['source'])))
                    if isinstance(node, ast.FunctionDef) and node.name == 'survivant')
    scope = {'pd': pd, 'REVUE': [], 'SOURCE_PRIORITAIRE': ['crm','cif']}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(notebook), 'exec'), scope)
    records = [
        {'groupe':'FIXTURE-1','source_systeme':'crm','source_id':'FICTION-A','telephone':'0123456789'},
        {'groupe':'FIXTURE-1','source_systeme':'cif','source_id':'FICTION-B','telephone':'0123456789'},
        {'groupe':'FIXTURE-1','source_systeme':'crm','source_id':'FICTION-C','telephone':'0198765432'},
    ]
    current_phone = '0198765432'  # Vérité déclarée de la fixture, aucune preuve sur une personne réelle.
    actual = scope['survivant'](pd.DataFrame(records), 'telephone', r'0[1-9]\d{8}').loc['FIXTURE-1']
    assert actual == '0123456789' and actual != current_phone
    return {
        'synthetique': True, 'nature': 'contre-exemple pédagogique exécuté de la fonction réelle survivant',
        'source': 'notebooks/S4_g02.ipynb::survivant',
        'fonction_sha256': hashlib.sha256(ast.dump(function,include_attributes=False).encode()).hexdigest(),
        'fixture': records, 'verite_fixture': {'telephone_courant':current_phone},
        'valeur_retenue':actual, 'erreur_fixture_demontree':True,
        'explication':'Deux fiches anciennes identiques remportent la fréquence contre une fiche courante ; validité de format et fréquence ne prouvent pas la fraîcheur.',
        'limites':'Données entièrement fictives ; aucune erreur de survie métier réelle confirmée, aucune confirmation humaine inventée.',
    }


if __name__ == '__main__':
    result = demonstrate()
    if '--write' in sys.argv:
        (ROOT / 'reports/AUDIT_survie_contre_exemple.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

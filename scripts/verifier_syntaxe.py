"""Vérifie la syntaxe du code livré, sans importer ni exécuter les notebooks."""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
python_count = notebook_cells = 0
for folder in ('pipelines','scripts','soda','tests'):
    for path in (ROOT / folder).glob('*.py'):
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        python_count += 1
for path in (ROOT / 'notebooks').glob('*.ipynb'):
    for index, cell in enumerate(json.loads(path.read_text(encoding='utf-8'))['cells']):
        if cell['cell_type'] == 'code' and ''.join(cell['source']).strip():
            ast.parse(''.join(cell['source']), filename=f'{path}:cellule-{index}')
            notebook_cells += 1
print(f'Syntaxe valide : {python_count} fichiers Python, {notebook_cells} cellules de notebooks.')

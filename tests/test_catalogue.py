"""Tests de la vraie interface Streamlit, sans base ni secrets."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / 'catalogue/app.py'


class CatalogueTests(unittest.TestCase):
    def test_each_object_and_responsibilities(self):
        import yaml
        catalogue = yaml.safe_load(APP.with_name('catalogue.yml').read_text())
        app = AppTest.from_file(str(APP)).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.selectbox[0].options), 5)
        for name in app.selectbox[0].options:
            app.selectbox[0].select(name).run()
            self.assertFalse(app.exception)
            text = '\n'.join(element.value for element in app.markdown)
            for expected in ('Ruth', 'Firdaouss', 'RQ-', '->', 'Couche : GOLD'):
                self.assertIn(expected, text)
            self.assertIn('Définitions', [s.value for s in app.subheader])
            self.assertEqual(app.subheader[0].value, name)
            fiche = catalogue['tables'][name]
            self.assertIn(fiche['description'], text)
            self.assertIn(', '.join(fiche['regles']), text)
            for definition in fiche.get('definitions', {}).values():
                self.assertIn(definition, text)
            for field in ('grain', 'cle', 'sensibilite'):
                if field in fiche:
                    self.assertIn(f"{field} : {fiche[field]}", text)
            for lineage in fiche['lineage']:
                self.assertIn(lineage, text)
            for other_name, other in catalogue['tables'].items():
                if other_name != name:
                    self.assertNotIn(other['description'], text)

    def test_invalid_and_missing_catalogue(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'catalogue.yml'
            for content in (None, '[invalide', 'tables: {}', 'tables:\n  x: []'):
                if content is not None:
                    path.write_text(content)
                with patch.dict(os.environ, {'DQ_CATALOGUE_PATH': str(path)}):
                    app = AppTest.from_file(str(APP)).run()
                self.assertFalse(app.exception)
                self.assertEqual(len(app.error), 1)


    def test_malformed_field_types_and_missing_required_fields(self):
        from copy import deepcopy
        import yaml
        valid = yaml.safe_load(APP.with_name('catalogue.yml').read_text())
        first = next(iter(valid['tables']))
        cases = []
        for roles in (None, [], ['data_owner'], {'data_owner': None}):
            data = deepcopy(valid); data['roles'] = roles; cases.append(data)
        for field, invalid in (
            ('proprietaire', []), ('steward', 'inconnu'),
            ('regles', 'RQ-001'), ('regles', [None]),
            ('lineage', 'source -> cible'), ('lineage', [{}]),
            ('definitions', []), ('definitions', {'x': None}),
            ('decisions', 'D-01'), ('couche', None), ('description', []),
        ):
            data = deepcopy(valid); data['tables'][first][field] = invalid; cases.append(data)
        for field in ('couche', 'description', 'proprietaire', 'steward', 'regles', 'lineage'):
            data = deepcopy(valid); del data['tables'][first][field]; cases.append(data)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'catalogue.yml'
            for index, data in enumerate(cases):
                with self.subTest(case=index):
                    path.write_text(yaml.safe_dump(data))
                    with patch.dict(os.environ, {'DQ_CATALOGUE_PATH': str(path)}):
                        app = AppTest.from_file(str(APP)).run()
                    self.assertFalse(app.exception)
                    self.assertEqual(len(app.error), 1)
                    self.assertFalse(app.selectbox)

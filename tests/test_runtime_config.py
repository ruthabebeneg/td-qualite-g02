"""Connexions sans secrets de repli ; aucun accès à MariaDB."""
import os
from pathlib import Path
import secrets
import sys
import tempfile
import unittest
from unittest.mock import patch

from sqlalchemy.engine import make_url
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'pipelines'))
import runtime_config as config


class RuntimeConfigTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.envfile = Path(self.directory.name) / '.env'
        self.enterContext(patch.object(config, 'ENV_FILE', self.envfile))
        self.enterContext(patch.dict(os.environ, {}, clear=True))

    def test_missing_secrets_fail_before_connection(self):
        for reader, name in [(False, 'MARIADB_ROOT_PASSWORD'), (True, 'DQ_READER_PASSWORD')]:
            with self.subTest(reader=reader), self.assertRaisesRegex(ValueError, name):
                config.database_url('bronze', reader=reader)

    def test_local_file_special_characters_and_no_environment_mutation(self):
        value = secrets.token_hex(12) + '@:/#é${NE_PAS_INTERPOLER}'
        self.envfile.write_text("MARIADB_ROOT_PASSWORD='" + value + "'\nDQ_DB_HOST=127.0.0.1\n")
        before = dict(os.environ)
        url = make_url(config.database_url('dq'))
        self.assertEqual(url.password, value)
        self.assertEqual((url.username, url.host, url.database), ('root', '127.0.0.1', 'dq'))
        self.assertEqual(dict(os.environ), before)

    def test_process_environment_has_priority_and_reader_is_separate(self):
        local = secrets.token_hex(12)
        admin = secrets.token_hex(12)
        reader = secrets.token_hex(12)
        self.envfile.write_text('MARIADB_ROOT_PASSWORD=' + local + '\n')
        os.environ.update(MARIADB_ROOT_PASSWORD=admin, DQ_READER_PASSWORD=reader, DQ_DB_HOST='mariadb')
        self.assertEqual(make_url(config.database_url()).password, admin)
        url = make_url(config.database_url('bronze', reader=True))
        self.assertEqual((url.username, url.password, url.host), ('reader', reader, 'mariadb'))

    def test_explicit_urls_are_preserved(self):
        os.environ.update(DQ_DB_URL='sqlite://', DQ_DATABASE_URL='sqlite:///:memory:')
        self.assertEqual(config.database_url('dq'), 'sqlite://')
        self.assertEqual(config.database_url('bronze', reader=True), 'sqlite:///:memory:')

    def test_explicit_loading_keeps_process_values_and_literal_dollar(self):
        value = secrets.token_hex(12) + '${NE_PAS_INTERPOLER}'
        self.envfile.write_text("DQ_READER_PASSWORD='" + value + "'\nDQ_DB_HOST=local\n")
        os.environ['DQ_DB_HOST'] = 'mariadb'
        config.load_local_env()
        self.assertEqual(config.required_env('DQ_READER_PASSWORD'), value)
        self.assertEqual(os.environ['DQ_DB_HOST'], 'mariadb')

    def test_empty_password_is_refused(self):
        self.envfile.write_text('MARIADB_ROOT_PASSWORD=\n')
        with self.assertRaisesRegex(ValueError, 'MARIADB_ROOT_PASSWORD'):
            config.database_url()

    def test_compose_and_soda_only_reference_environment_secrets(self):
        compose = yaml.safe_load((ROOT / 'docker-compose.yml').read_text())
        maria = compose['services']['mariadb']['environment']
        jupyter = compose['services']['jupyter']['environment']
        self.assertEqual(maria['MARIADB_ROOT_PASSWORD'], '${MARIADB_ROOT_PASSWORD:?MARIADB_ROOT_PASSWORD requis}')
        self.assertEqual(maria['DQ_READER_PASSWORD'], '${DQ_READER_PASSWORD:?DQ_READER_PASSWORD requis}')
        self.assertEqual(jupyter['JUPYTER_TOKEN'], '${JUPYTER_TOKEN:?JUPYTER_TOKEN requis}')
        for name in ('MARIADB_ROOT_PASSWORD', 'DQ_READER_PASSWORD'):
            self.assertEqual(jupyter[name], maria[name])
        for connection in yaml.safe_load((ROOT / 'soda/configuration.yml').read_text()).values():
            self.assertEqual(connection['password'], '${MARIADB_ROOT_PASSWORD}')
        example = (ROOT / '.env.example').read_text()
        for name in ('MARIADB_ROOT_PASSWORD', 'DQ_READER_PASSWORD', 'JUPYTER_TOKEN'):
            self.assertIn(name + '=\n', example)

    def test_init_reader_transmits_only_hex_sql_and_no_password_literal(self):
        import subprocess
        script = ROOT / 'initdb/02_reader.sh'
        value = secrets.token_hex(12) + "'\\$;é"
        os.environ['DQ_READER_PASSWORD'] = value
        wrapper = 'docker_process_sql() { cat; }; source "$1"'
        result = subprocess.run(['bash', '-c', wrapper, 'test', str(script)], capture_output=True, text=True, check=True)
        self.assertNotIn(value, result.stdout)
        self.assertIn('0x' + value.encode().hex(), result.stdout)
        self.assertIn('QUOTE(@reader_password)', result.stdout)
        self.assertIn('PREPARE reader_statement FROM @reader_sql;', result.stdout)
        self.assertIn('EXECUTE reader_statement;', result.stdout)
        self.assertIn('DEALLOCATE PREPARE reader_statement;', result.stdout)
        self.assertIn('GRANT SELECT ON bronze.*', result.stdout)
        self.assertNotIn('IDENTIFIED BY', (ROOT / 'initdb/00_medallion.sql').read_text())

    def test_soda_child_receives_local_environment(self):
        import importlib.util
        import json
        import subprocess
        key = secrets.token_hex(12)
        self.envfile.write_text('MARIADB_ROOT_PASSWORD=' + key + '\nDQ_DB_HOST=local-test\n')
        executable = Path(self.directory.name) / 'soda'
        executable.write_text(
            '#!' + sys.executable + '\n'
            'import os, sys, json\n'
            'from pathlib import Path\n'
            'if os.environ.get("MARIADB_ROOT_PASSWORD") != ' + repr(key) + ': raise SystemExit(7)\n'
            'if os.environ.get("DQ_DB_HOST") != "local-test": raise SystemExit(8)\n'
            'Path(sys.argv[sys.argv.index("-srf") + 1]).write_text(json.dumps({"hasErrors":False,"hasFailures":False}))\n'
        )
        executable.chmod(0o700)
        os.environ['PATH'] = self.directory.name + os.pathsep + os.defpath
        spec = importlib.util.spec_from_file_location('runtime_soda_scan', ROOT / 'soda/run_scan.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(sys, 'argv', ['run_scan', '-d', 'crm', '-c', 'configuration.yml', 'checks.yml']):
            self.assertEqual(module.main(), 0)



if __name__ == '__main__':
    unittest.main()

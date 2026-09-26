"""Every demo process starts from a freshly seeded temporary database."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DemoLaunchTests(unittest.TestCase):
    def test_launch_replaces_inherited_database_path_with_fresh_synthetic_file(self):
        self.assertTrue((ROOT / "demo/launch.py").is_file(), "missing safe demo launcher")
        code = '''
import os, sqlite3, tempfile
from pathlib import Path
from unittest.mock import patch
from demo.launch import main
with tempfile.TemporaryDirectory() as directory:
    inherited = Path(directory) / 'not-for-demo.db'
    inherited.write_bytes(b'do not read or overwrite')
    os.environ['DEMO_DB_PATH'] = str(inherited)
    seen = {}
    def capture_run(app, **kwargs):
        path = Path(os.environ['DEMO_DB_PATH'])
        assert path != inherited and path.is_file()
        con = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
        assert con.execute('SELECT COUNT(*) FROM messages').fetchone()[0] == 100
        con.close()
        seen['path'] = path
        seen['port'] = kwargs['port']
    with patch('uvicorn.run', capture_run):
        main()
    assert not seen['path'].exists() and inherited.read_bytes() == b'do not read or overwrite'
    assert os.environ['DEMO_DB_PATH'] == str(inherited)
'''
        env = dict(os.environ)
        env.pop("DEMO_DB_PATH", None)
        result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True)
        self.assertEqual(result.returncode, 0, "launcher must replace inherited paths only inside its process")


if __name__ == "__main__":
    unittest.main()

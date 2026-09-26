"""Only the reviewed demo build can be served; admin routes remain absent."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StaticFrontendTests(unittest.TestCase):
    def test_vite_build_is_served_without_exposing_hidden_files_or_admin(self):
        self.assertTrue((ROOT / "app/dist/index.html").is_file(), "build frontend before running static smoke")
        code = '''
import os, tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from demo.seed import build_demo_database
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory)/'fictional.db'
    build_demo_database(path)
    os.environ['DEMO_DB_PATH'] = str(path)
    from demo.app import app
    with TestClient(app) as client:
        page = client.get('/')
        assert page.status_code == 200 and 'Gemesis Vault' in page.text
        asset = client.get('/gemesislogo.jpg')
        assert asset.status_code == 200 and asset.headers['content-type'].startswith('image/')
        assert client.get('/admin').status_code in (403,404)
        assert client.get('/.env').status_code in (403,404)
'''
        result = subprocess.run([sys.executable, "-c", code], cwd=ROOT,
                                env={k: v for k, v in os.environ.items() if k != "DEMO_DB_PATH"},
                                capture_output=True)
        self.assertEqual(result.returncode, 0, "serve demo assets without exposing owner/config routes")


if __name__ == "__main__":
    unittest.main()

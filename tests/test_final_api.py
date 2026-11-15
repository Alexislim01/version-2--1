import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend.main import app
from backend import final_api


class FinalAPITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patch = patch.object(final_api, 'JOBS', self.root)
        self.patch.start()
        self.active = final_api.ACTIVE
        final_api.ACTIVE = None
        self.client = TestClient(app)

    def tearDown(self):
        final_api.ACTIVE = self.active
        self.patch.stop()
        self.tmp.cleanup()

    def job(self, status='complete'):
        name = 'a' * 32
        path = self.root / name
        path.mkdir()
        final_api.save(path, {'id': name, 'status': status, 'stage': 'Finished'})
        (path / 'output').mkdir()
        (path / 'output' / 'calendar.csv').write_text('year,value\n2003,12', encoding='utf8')
        return name, path

    def test_capabilities_and_strict_run_options(self):
        response = self.client.get('/api/final/status')
        self.assertEqual(response.status_code, 200)
        for options in [{'country': '../../other'}, {'trees': 4}, {'profile': 'shell'}, {'unknown': 1}, {'country': 'Indonesia'}]:
            self.assertEqual(self.client.post('/api/final/jobs', json=options).status_code, 422)

    def test_reject_cross_origin_computation(self):
        response = self.client.post('/api/final/jobs', json={}, headers={'Origin': 'https://unrelated.example'})
        self.assertEqual(response.status_code, 403)

    def test_start_reserves_slot_and_preserves_delivered_results(self):
        with patch.object(final_api.threading, 'Thread') as thread, patch.object(final_api, 'missing_dependencies', return_value=[]):
            response = self.client.post('/api/final/jobs', json={'profile': 'features'})
            self.assertEqual(response.status_code, 202, response.text)
            self.assertEqual(final_api.ACTIVE, response.json()['id'])
            thread.return_value.start.assert_called_once()
            self.assertTrue((self.root / response.json()['id'] / 'status.json').exists())
            self.assertEqual(self.client.post('/api/final/jobs', json={}).status_code, 409)

    def test_files_and_path_traversal(self):
        job_id, path = self.job()
        (path / 'secret.txt').write_text('private')
        response = self.client.get(f'/api/final/jobs/{job_id}')
        self.assertEqual(len(response.json()['files']), 1)
        self.assertEqual(self.client.get(f'/api/final/jobs/{job_id}/files/calendar.csv').status_code, 200)
        for name in ['../secret.txt', '../../secret.txt', 'C:/Windows/win.ini']:
            with self.assertRaises(Exception):
                final_api.safe_file(path / 'output', name)
        self.assertEqual(self.client.get('/api/final/jobs/not-a-run').status_code, 404)

    def test_cancel_and_interrupted_recovery(self):
        job_id, path = self.job('running')
        self.assertEqual(self.client.get(f'/api/final/jobs/{job_id}').json()['status'], 'interrupted')
        final_api.ACTIVE = job_id
        response = self.client.post(f'/api/final/jobs/{job_id}/cancel')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(final_api.read(path)['status'], 'cancelled')
        self.assertEqual(self.client.post(f'/api/final/jobs/{job_id}/cancel').status_code, 409)

    def test_bundle_only_exposed_after_success(self):
        job_id, path = self.job('running')
        self.assertEqual(self.client.get(f'/api/final/jobs/{job_id}/bundle/manifest.json').status_code, 409)
        (path / 'bundle').mkdir()
        (path / 'bundle' / 'manifest.json').write_text(json.dumps({'schema': 1}))
        final_api.save(path, {'id': job_id, 'status': 'complete', 'bundle': '/api/final/jobs/' + job_id + '/bundle/'})
        self.assertEqual(self.client.get(f'/api/final/jobs/{job_id}/bundle/manifest.json').json(), {'schema': 1})

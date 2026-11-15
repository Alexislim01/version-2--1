import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app, query
from test_pipeline import record


class APITests(unittest.TestCase):
    def setUp(self):
        query.cache_clear()
        self.mock=patch('backend.main.dataset',return_value=([record()],[{'sensor':'MODIS','start':'2020-07-01','end':'2020-07-02','country':'Malaysia'}]))
        self.mock.start()
        self.client=TestClient(app)

    def tearDown(self):
        self.mock.stop()
        query.cache_clear()

    def test_all_documented_routes_and_openapi(self):
        for route in ['calendar','timeseries','anomalies','critical-periods','hotspots','calibration','grid']:
            with self.subTest(route=route):
                response=self.client.get(f'/api/{route}',params={'start':'2020-07-01','end':'2020-07-03'})
                self.assertEqual(response.status_code,200,response.text)
        self.assertIn('/api/calendar',self.client.get('/openapi.json').json()['paths'])

    def test_calendar_preserves_missing_days(self):
        days=self.client.get('/api/calendar?start=2020-07-01&end=2020-07-03').json()['days']
        self.assertEqual([d['harmonized_count'] for d in days],[1,0,None])

    def test_hotspots_date_and_geojson(self):
        data=self.client.get('/api/hotspots?start=2020-07-01&end=2020-07-03&date=2020-07-01').json()
        self.assertEqual(data['type'],'FeatureCollection')
        self.assertEqual(data['features'][0]['geometry']['coordinates'],[113.01,2.01])
        self.assertEqual(len(self.client.get('/api/hotspots?date=2020-07-02').json()['features']),0)

    def test_invalid_requests_return_422(self):
        for params in [{'aoi':'invalid'},{'grid':.3},{'start':'oops'},{'start':'2021-01-01','end':'2020-01-01'},
                       {'aoi':'-180,-90,180,90'},{'sensors':'Landsat'},{'confidence':0},{'metric':'energy'}]:
            with self.subTest(params=params):
                self.assertEqual(self.client.get('/api/calendar',params=params).status_code,422)

    def test_browser_dataset_preserves_native_confidence_for_browser_filters(self):
        rows = [record(confidence='0'), record(instrument='VIIRS', confidence='low', satellite='N'),
                record(instrument='VIIRS', confidence='unknown', satellite='N20'), record(latitude='nan')]
        with patch('backend.main.dataset', return_value=(rows, [])):
            response = self.client.get('/api/dataset')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['rows']), 3)
        self.assertEqual({r[6] for r in response.json()['rows']}, {'0', 'l', 'unknown'})

    def test_unsupported_region_has_no_coverage(self):
        days=self.client.get('/api/calendar?aoi=california&start=2020-07-01&end=2020-07-03').json()['days']
        self.assertTrue(all(d['harmonized_count'] is None for d in days))


if __name__=='__main__':
    unittest.main()

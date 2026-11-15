"""Synthetic fixtures verify math only; the application ships real NASA data."""
import math
import unittest
from pipeline.core import analyze, clean, fit_transfer, grid_records, in_geometry


def record(**changes):
    return {'latitude': 2.01, 'longitude': 113.01, 'acq_date': '2020-07-01', 'acq_time': '1230',
            'satellite': 'Aqua', 'instrument': 'MODIS', 'confidence': '80', 'frp': '10', 'daynight': 'D', **changes}


class PipelineTests(unittest.TestCase):
    def test_clean_confidence_duplicates_and_invalid_values(self):
        rows = [record(), record(), record(confidence='29'), record(latitude='nan'),
                record(instrument='VIIRS', confidence='l'), record(instrument='VIIRS', confidence='nominal'),
                record(frp='-1'), record(acq_time='2460')]
        accepted = clean(rows)
        self.assertEqual(len(accepted), 2)
        self.assertEqual({r['instrument'] for r in accepted}, {'MODIS', 'VIIRS'})
        self.assertEqual(len(clean(rows, 90)), 0)

    def test_viirs_satellites_merge_without_adding_frp(self):
        rows = clean([record(instrument='VIIRS', confidence='n', satellite='N', frp=10),
                      record(instrument='VIIRS', confidence='h', satellite='N20', frp=14)])
        cells = grid_records(rows)
        self.assertEqual(cells[0]['detection_count'], 2)
        self.assertEqual(cells[0]['unique_pixels'], 1)
        self.assertEqual(cells[0]['frp'], 14)

    def test_gridding_handles_negative_coordinates(self):
        cell = grid_records(clean([record(latitude=-.01, longitude=-.26)]), .25)[0]
        self.assertEqual(cell['cell'], [-1, -2])
        with self.assertRaises(ValueError):
            grid_records([], .3)

    def test_theil_sen_recovers_relationship_despite_outlier(self):
        fit = fit_transfer([(x, 2*x+3) for x in range(1, 50)]+[(50, 10000)])
        self.assertTrue(fit['available'])
        self.assertAlmostEqual(fit['slope'], 2)
        self.assertAlmostEqual(fit['intercept'], 3)
        self.assertTrue(math.isfinite(fit['r2']))

    def test_insufficient_overlap_is_not_a_calibration(self):
        self.assertFalse(fit_transfer([(1, 2)]*30)['available'])
        self.assertFalse(fit_transfer([(x, 2*x) for x in range(10)])['available'])

    def test_missing_coverage_remains_missing(self):
        a = analyze([], [], '2020-01-01', '2020-01-03', [108,-5,120,8])
        self.assertTrue(all(d['harmonized_count'] is None for d in a['series']))
        covered = [{'sensor':'MODIS','start':'2020-01-01','end':'2020-01-02'}]
        a = analyze([], covered, '2020-01-01', '2020-01-03', [108,-5,120,8])
        self.assertEqual([d['harmonized_count'] for d in a['series']], [0, 0, None])

    def test_uncalibrated_viirs_is_never_substituted_as_modis(self):
        a = analyze([record(instrument='VIIRS',confidence='n')], [{'sensor':'VIIRS','start':'2020-07-01','end':'2020-07-01'}], '2020-07-01','2020-07-01',[108,-5,120,8])
        self.assertEqual(a['series'][0]['viirs'], 1)
        self.assertIsNone(a['series'][0]['harmonized_count'])
        self.assertEqual(a['series'][0]['source'], 'Uncalibrated VIIRS')

    def test_polygon_holes_filter_observations(self):
        polygon={'type':'Polygon','coordinates':[[[110,0],[115,0],[115,5],[110,5],[110,0]],[[112,1],[114,1],[114,3],[112,3],[112,1]]]}
        self.assertFalse(in_geometry(record(),polygon))
        self.assertTrue(in_geometry(record(longitude=111),polygon))

    def test_anomaly_excludes_current_year_and_flags_real_exceedance(self):
        coverage=[{'sensor':'MODIS','start':'2019-01-01','end':'2021-12-31'}]
        rows=[record(acq_date='2021-07-01',latitude=2+i*.02) for i in range(20)]
        a=analyze(rows,coverage,'2019-01-01','2021-12-31',[108,-5,120,8])
        day=next(d for d in a['series'] if d['date']=='2021-07-01')
        self.assertTrue(day['unusual'])
        self.assertEqual(day['median'],0)
        self.assertEqual(day['p95'],0)
        self.assertEqual(day['percentile'],100)

    def test_invalid_bounds_and_dates_are_rejected(self):
        with self.assertRaises(ValueError):
            analyze([],[],'2021-01-01','2020-01-01',[108,-5,120,8])
        with self.assertRaises(ValueError):
            analyze([],[],'2020-01-01','2020-01-02',[120,-5,108,8])


if __name__=='__main__':
    unittest.main()

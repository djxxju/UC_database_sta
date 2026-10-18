import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_pilot import quadratic
from validate import ROOT, capacity_upper_screen, load, validate_data, unique_object


class ProfileTests(unittest.TestCase):
    def setUp(self):
        directory = ROOT / 'cases' / 'orlib_10_0_4_w_quad_v1'
        self.u, self.s, self.p = [load(directory / name) for name in
                                 ['units.json', 'stochastic.json', 'provenance.json']]

    def reject(self, edit):
        u, s, p = copy.deepcopy((self.u, self.s, self.p))
        edit(u, s, p)
        with self.assertRaises(ValueError):
            validate_data(u, s, p)

    def test_delivery(self):
        validate_data(self.u, self.s, self.p)

    def test_array_length(self):
        self.reject(lambda u, s, p: u['pmin'].pop())

    def test_duplicate_scenario(self):
        def edit(u, s, p):
            s['scenarios'][0]['probability'] = 0.5
            s['scenarios'].append(dict(s['scenarios'][0]))
        self.reject(edit)

    def test_probability_sum(self):
        self.reject(lambda u, s, p: s['scenarios'][0].update(probability=0.99999))

    def test_load_and_factor_exclusive(self):
        self.reject(lambda u, s, p: s['scenarios'][0].update(load=[1]*24))

    def test_explicit_load_length(self):
        def edit(u, s, p):
            s['scenarios'][0].pop('load_factor')
            s['scenarios'][0]['load'] = [1]*23
        self.reject(edit)

    def test_negative_load(self):
        self.reject(lambda u, s, p: u['base_load'].__setitem__(0, -1))

    def test_bool_is_not_unit_count(self):
        self.reject(lambda u, s, p: u.update(n_units=True))

    def test_capacity_order(self):
        self.reject(lambda u, s, p: u['pstart'].__setitem__(0, u['pmax'][0]+1))

    def test_initial_output(self):
        def edit(u, s, p):
            u['initial_duration'][0] = -1
            u['initial_output'][0] = 1
        self.reject(edit)

    def test_nonfinite(self):
        self.reject(lambda u, s, p: u['cost_a'].__setitem__(0, float('nan')))

    def test_cold_fields_paired(self):
        self.reject(lambda u, s, p: u.update(cold_startup_cost=[1]*u['n_units']))

    def test_cold_fee_order(self):
        def edit(u, s, p):
            u['cold_startup_cost'] = [0]*u['n_units']
            u['cold_start_hours'] = [0]*u['n_units']
        self.reject(edit)

    def test_mapping_order(self):
        self.reject(lambda u, s, p: p['unit_mapping'][0].update(array_index=1))

    def test_duplicate_json_key(self):
        with self.assertRaises(ValueError):
            json.loads('{"x":1,"x":2}', object_pairs_hook=unique_object)

    def test_cost_interpolation_is_not_pwl_equivalence(self):
        coef, report = quadratic([0, 1, 2], [0, 1, 4])
        self.assertEqual(coef, [1.0, 0.0, 0.0])
        self.assertAlmostEqual(report['max_abs_cost_delta_per_hour'], 0.25)
        self.assertFalse(report['equivalent_to_source_pwl'])

    def test_nonquadratic_knots_rejected(self):
        with self.assertRaises(ValueError):
            quadratic([0, 1, 2, 3, 4], [0, 1, 5, 10, 20])

    def test_capacity_screen_failure_not_solver_status(self):
        u = copy.deepcopy(self.u)
        u['base_load'] = [1e9]*24
        result = capacity_upper_screen(u)
        self.assertEqual(result['status'], 'failed_necessary_condition')
        self.assertFalse(result['feasibility_proven'])


if __name__ == '__main__':
    unittest.main()

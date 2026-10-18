"""Validate the SJTU hourly delivery profile; never build or solve a UC model."""
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if (ROOT / '.tools').exists():
    sys.path.insert(0, str(ROOT / '.tools'))
from jsonschema import Draft202012Validator


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'),
                      object_pairs_hook=unique_object,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def finite(value):
    if isinstance(value, dict):
        for item in value.values():
            finite(item)
    elif isinstance(value, list):
        for item in value:
            finite(item)
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError('Non-finite JSON number')


def validate_data(units, stochastic, provenance):
    for name, data in [('units', units), ('stochastic', stochastic), ('provenance', provenance)]:
        finite(data)
        schema = load(ROOT / 'schema' / f'{name}.schema.json')
        Draft202012Validator.check_schema(schema)
        errors = list(Draft202012Validator(schema).iter_errors(data))
        if errors:
            raise ValueError(f'{name}: {errors[0].json_path}: {errors[0].message}')
    n, horizon = units['n_units'], units['horizon']
    if 'initial_output' not in units:
        raise ValueError('Pilot deliveries require explicit initial_output; reference permits omission')
    for key, values in units.items():
        if isinstance(values, list):
            expected = horizon if key == 'base_load' else n
            if len(values) != expected:
                raise ValueError(f'{key}: expected {expected} values')
    for i in range(n):
        if any(units[key][i] > units['pmax'][i] for key in ['pmin', 'pstart', 'pshut']):
            raise ValueError(f'Unit {i}: capacity ordering')
        out, duration = units['initial_output'][i], units['initial_duration'][i]
        if duration <= 0 and out != 0:
            raise ValueError(f'Unit {i}: offline initial output')
        if duration > 0 and not units['pmin'][i] <= out <= units['pmax'][i]:
            raise ValueError(f'Unit {i}: online initial output outside bounds')
        if 'cold_startup_cost' in units and units['cold_startup_cost'][i] < units['startup_cost'][i]:
            raise ValueError(f'Unit {i}: cold startup cost below hot startup cost')
    scenarios = stochastic['scenarios']
    if len({s['name'] for s in scenarios}) != len(scenarios):
        raise ValueError('Duplicate scenario name')
    if abs(math.fsum(s['probability'] for s in scenarios) - 1) > 1e-9:
        raise ValueError('Scenario probabilities do not sum to 1 within 1e-9')
    for s in scenarios:
        if 'load' in s and len(s['load']) != horizon:
            raise ValueError('Scenario load length differs from horizon')
    mapping = provenance['unit_mapping']
    if len(mapping) != n or [m['array_index'] for m in mapping] != list(range(n)):
        raise ValueError('Unit mapping is not a complete zero-based ordered list')
    if len({m['source_unit_id'] for m in mapping}) != n:
        raise ValueError('Repeated source unit identifier')


def capacity_upper_screen(units):
    """Optimistic bound under documented ordinary ramping across startup.

    Ignore shutdowns, downward ramps and many restrictions. Failure is a
    necessary-condition warning under that interpretation; success proves no
    feasibility. Not a solver or a test of the unavailable target program.
    """
    upper = []
    for t in range(1, units['horizon'] + 1):
        available = 0.0
        for i in range(units['n_units']):
            r, maximum = units['ramp_up'][i], units['pmax'][i]
            duration = units['initial_duration'][i]
            if duration > 0:
                available += min(maximum, units['initial_output'][i] + t * r)
            elif units['pmin'][i] <= min(r, units['pstart'][i]):
                remaining = max(0, units['min_down'][i] + duration)
                k = max(0, t - remaining)
                available += 0 if k == 0 else min(maximum, units['pstart'][i] + (k - 1) * r, k * r)
        upper.append(available)
    violations = [{'hour': t + 1, 'load': d, 'optimistic_upper_mw': b}
                  for t, (d, b) in enumerate(zip(units['base_load'], upper)) if d > b + 1e-7]
    return {'status': 'failed_necessary_condition' if violations else 'passed_necessary_condition_only',
            'interpretation': 'documented ordinary output ramp also applies during startup; no target code inspected',
            'violations': violations, 'feasibility_proven': False}


def validate_case(directory):
    directory = Path(directory)
    units, stochastic, provenance = [load(directory / name) for name in
                                     ['units.json', 'stochastic.json', 'provenance.json']]
    validate_data(units, stochastic, provenance)
    for row in provenance['source_files']:
        path = (directory / row['path']).resolve()
        if not path.is_relative_to(ROOT.resolve()):
            raise ValueError('Original file path outside delivery repository')
        if sha(path) != row['sha256']:
            raise ValueError('Original source hash mismatch')
    for name, expected in provenance['output_sha256'].items():
        if name not in ('units.json', 'stochastic.json') or sha(directory / name) != expected:
            raise ValueError('Output hash mismatch')
    return {'case_id': provenance['case_id'], 'json_schema': 'passed',
            'cross_field_checks': 'passed', 'source_and_output_hashes': 'passed',
            'capacity_upper_screen': capacity_upper_screen(units),
            'classification': provenance['classification'], 'solve_status': 'not_run',
            'target_program_import': 'not_tested', 'independent_solution_check': 'not_run'}


def main():
    reports = [validate_case(d) for d in sorted((ROOT / 'cases').iterdir()) if d.is_dir()]
    text = json.dumps({'profile': 'sjtu-hourly-uc/0.1.0', 'cases': reports}, ensure_ascii=False, indent=2) + '\n'
    (ROOT / 'reports' / 'validation.json').write_text(text, encoding='utf-8', newline='\n')
    print(text)


if __name__ == '__main__':
    main()

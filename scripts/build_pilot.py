"""Reproduce two derived hourly UC deliveries from hash-pinned originals.

Only read sources/. No original repository writes, downloads or solver calls.
"""
from decimal import Decimal, localcontext
import gzip
import json
from pathlib import Path
from validate import ROOT, load, sha

PROFILE = 'sjtu-hourly-uc/0.1.0'
CODE_VERSION = 'pilot-converter/0.1.0'


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, allow_nan=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def quadratic(xs, ys):
    """Interpolate first/middle/last; require all knots to agree to 1e-7.

    This recovers a quadratic through knots, NOT an equivalent PWL function.
    Report exact per-segment maxima of the resulting cost-function change.
    """
    if len(xs) != len(ys) or len(xs) < 3 or any(x2 <= x1 for x1, x2 in zip(xs, xs[1:])):
        raise ValueError('Need at least three strictly increasing cost knots')
    idx = [0, len(xs) // 2, len(xs) - 1]
    with localcontext() as context:
        context.prec = 40
        x0, x1, x2 = [Decimal(str(xs[i])) for i in idx]
        y0, y1, y2 = [Decimal(str(ys[i])) for i in idx]
        a = ((y2-y1)/(x2-x1) - (y1-y0)/(x1-x0))/(x2-x0)
        b = (y1-y0)/(x1-x0) - a*(x0+x1)
        c = y0 - a*x0*x0 - b*x0
        coefficients = [float(v) for v in [a, b, c]]
    if any(v < 0 for v in coefficients):
        raise ValueError('Negative target cost coefficient; no silent clipping')
    a, b, c = coefficients
    f = lambda x: a*x*x + b*x + c
    residual = max(abs(f(x)-y) for x, y in zip(xs, ys))
    if residual > 1e-7:
        raise ValueError('Knots do not lie on one nonnegative quadratic within 1e-7')
    maxima = []
    for left, right, yl, yr in zip(xs, xs[1:], ys, ys[1:]):
        slope = (yr-yl)/(right-left)
        candidates = [left, right]
        if a != 0:
            stationary = (slope-b)/(2*a)
            if left <= stationary <= right:
                candidates.append(stationary)
        values = [(abs(f(x) - (yl+slope*(x-left))), x) for x in candidates]
        err, at = max(values)
        maxima.append({'left_mw': left, 'right_mw': right, 'max_abs_cost_delta_per_hour': err,
                       'at_mw': at, 'target_minus_source_at_max': f(at)-(yl+slope*(at-left))})
    return coefficients, {'method': 'Decimal 40-digit interpolation at first, middle and last knots; verify every knot',
                           'knot_residual_max': residual, 'knot_residual_acceptance': 1e-7,
                           'max_abs_cost_delta_per_hour': max(x['max_abs_cost_delta_per_hour'] for x in maxima),
                           'segment_deviations': maxima, 'source_mw_knots': xs, 'source_cost_knots': ys,
                           'equivalent_to_source_pwl': False}


def convert(row):
    path = ROOT / row['path']
    if sha(path) != row['sha256']:
        raise ValueError('Source identity changed')
    data = json.loads(gzip.decompress(path.read_bytes()))
    allowed = {'LICENSE', 'SOURCE', 'Parameters', 'Generators', 'Buses', 'Reserves'}
    if set(data) != allowed or len(data['Buses']) != 1:
        raise ValueError('Unsupported source sections; no silent dropping')
    if 'Permission is hereby granted' not in data['LICENSE']:
        raise ValueError('Expected explicit per-file license missing')
    params = data['Parameters']
    if params != {'Time (h)': 24, 'Version': '0.3'}:
        raise ValueError('Only pinned 24-hour source-format 0.3 pilot supported')
    reserve = list(data['Reserves'].values())
    if len(reserve) != 1 or reserve[0]['Type'] != 'Spinning' or any(reserve[0]['Amount (MW)']):
        raise ValueError('Only zero-reserve pilot supported; never drop positive reserve')
    ids = list(data['Generators'])
    u = {'n_units': len(ids), 'horizon': 24,
         'base_load': list(next(iter(data['Buses'].values()))['Load (MW)'])}
    fields = ['pmin', 'pmax', 'pstart', 'pshut', 'ramp_up', 'ramp_down', 'min_up', 'min_down',
              'initial_duration', 'cost_a', 'cost_b', 'cost_c', 'startup_cost', 'shutdown_cost', 'initial_output']
    u.update({key: [] for key in fields})
    fits = []
    expected_keys = {'Bus', 'Production cost curve (MW)', 'Production cost curve ($)', 'Initial status (h)',
                     'Initial power (MW)', 'Minimum uptime (h)', 'Minimum downtime (h)', 'Reserve eligibility',
                     'Startup costs ($)', 'Startup delays (h)', 'Ramp up limit (MW)', 'Ramp down limit (MW)'}
    for gid in ids:
        g = data['Generators'][gid]
        if set(g) != expected_keys or g['Bus'] not in data['Buses']:
            raise ValueError('Unsupported generator properties')
        if len(g['Startup costs ($)']) != 1 or g['Startup delays (h)'] != [g['Minimum downtime (h)']]:
            raise ValueError('Only single fixed startup charge supported')
        if g['Reserve eligibility'] != list(data['Reserves']):
            raise ValueError('Unexpected reserve eligibility')
        coeff, fit = quadratic(g['Production cost curve (MW)'], g['Production cost curve ($)'])
        fits.append(dict(source_unit_id=gid, coefficients=dict(zip(['cost_a', 'cost_b', 'cost_c'], coeff)), **fit))
        values = dict(pmin=g['Production cost curve (MW)'][0], pmax=g['Production cost curve (MW)'][-1],
                      pstart=g['Production cost curve (MW)'][-1], pshut=g['Production cost curve (MW)'][-1],
                      ramp_up=g['Ramp up limit (MW)'], ramp_down=g['Ramp down limit (MW)'],
                      min_up=g['Minimum uptime (h)'], min_down=g['Minimum downtime (h)'],
                      initial_duration=g['Initial status (h)'], initial_output=g['Initial power (MW)'],
                      cost_a=coeff[0], cost_b=coeff[1], cost_c=coeff[2],
                      startup_cost=g['Startup costs ($)'][0], shutdown_cost=0.0)
        if values['initial_duration'] == 0:
            raise ValueError('Unknown/zero initial history is not accepted in this pilot')
        for key, value in values.items():
            u[key].append(value)
    stochastic = {'reserve_fraction': 0.0, 'scenarios': [{'name': 'base', 'probability': 1.0, 'load_factor': 1.0}]}
    directory = ROOT / 'cases' / row['case_id']
    write(directory / 'units.json', u)
    write(directory / 'stochastic.json', stochastic)
    p = {'case_id': row['case_id'], 'profile_version': PROFILE, 'classification': 'derived_model_changed',
         'source_case': row['source_case'], 'source_format_version': '0.3',
         'source_files': [{'path': '../../' + row['path'], 'sha256': row['sha256'],
                           'official_url': row['official_url'], 'collected_at_utc': row['collected_at_utc']}],
         'license': {'identifier': 'MIT', 'evidence': 'Explicit LICENSE text embedded in each original JSON',
                     'full_notice': '../../sources/ORLIB_LICENSE.txt', 'scope': 'These selected per-file licensed instances only'},
         'references': data['SOURCE'].splitlines(),
         'unit_mapping': [{'array_index': i, 'source_unit_id': gid} for i, gid in enumerate(ids)],
         'units': {'power': 'MW', 'time_step_hours': 1, 'currency': 'source_$',
                   'currency_note': 'Dollar label inherited unchanged; ISO currency and price year not independently established. No FX conversion.',
                   'cost_a': 'source_$/(MW^2*h)', 'cost_b': 'source_$/(MW*h)', 'cost_c': 'source_$/h',
                   'startup_cost': 'source_$/event', 'shutdown_cost': 'source_$/event'},
         'field_mapping': {
             'n_units': 'count(Generators); preserve source object insertion order',
             'horizon': 'Parameters.Time (h)', 'base_load': 'single Buses.*.Load (MW), no aggregation',
             'pmin,pmax': 'first and last Production cost curve (MW) knots',
             'pstart,pshut': 'pmax as effective finite bound; absent source startup/shutdown limits default to 1e6 in pinned reader',
             'ramp_up,ramp_down': 'Ramp up/down limit (MW), unchanged values; target startup semantics differ',
             'min_up,min_down': 'Minimum uptime/downtime (h), unchanged integers',
             'initial_duration,initial_output': 'Initial status (h), Initial power (MW), unchanged',
             'cost_a,cost_b,cost_c': 'quadratic interpolation through cost knots, report below; do not add a second no-load charge',
             'startup_cost': 'only Startup costs ($) entry', 'shutdown_cost': 'explicit zero-charge target assumption; no source shutdown-cost field',
             'reserve_fraction': 'all original spinning-reserve MW entries exactly zero -> 0.0',
             'scenarios': 'single deterministic source -> one base scenario with probability 1'},
         'assumptions': [
             'Absent shutdown charge is represented as 0, an explicit model assumption rather than a recovered historical cost.',
             'pstart/pshut cap at pmax replaces absent/very large source limits within static output bounds; ordinary target ramps still apply.',
             'Currency is retained as source dollar units, not silently converted into CNY or assigned a price year.'],
         'model_differences': [
             'Source UC.jl cost is PWL between knots; target quadratic differs inside segments even when all knots match.',
             'Target ordinary ramps also apply to startup/shutdown; source has separate startup/shutdown treatment.',
             'Target prohibits shutdown in last hour and truncates terminal min-up/down constraints; source equivalence not certified.',
             'Pinned source reader permits power imbalance at default penalty 1000; target interface has no imbalance penalty input.',
             'No target model code was supplied; physical feasibility and solver compatibility remain unverified.'],
         'unsupported_source_constraints': [], 'missing_source_fields': ['Startup limit (MW)', 'Shutdown limit (MW)', 'shutdown cost'],
         'cost_conversion': fits,
         'status': {'format_checks': 'see validation.json', 'solve_status': 'not_run', 'target_program_import': 'not_tested'},
         'target_rules': {'last_hour_shutdown': 'forbidden', 'terminal_min_up_down': 'truncated',
                          'ordinary_ramps_during_transitions': True, 'commitment': 'shared across all scenarios'},
         'converter': {'version': CODE_VERSION, 'path': '../../scripts/build_pilot.py',
                       'sha256': sha(Path(__file__)), 'profile_reference': 'https://notes.sjtu.edu.cn/s/zzB-Iq_eRD'},
         'output_sha256': {name: sha(directory / name) for name in ['units.json', 'stochastic.json']}}
    write(directory / 'provenance.json', p)
    directory.joinpath('README.md').write_text(
        f'# {row["case_id"]}\n\n源：{row["source_case"]}；{len(ids)} 台机组，24 个小时。\n\n'
        '本例是 `derived_model_changed` 派生试点。三份 JSON 必须配合 provenance 使用；'
        '来源原包位于 ../../sources/or-lib，原件未修改。\n\n'
        '成本由原分段线性节点重建为二次式，区间内有费用变化；普通爬坡、初末边界与功率失配处理也存在模型差异。'
        '完整映射、逐机成本误差与假设见 provenance.json。\n\n'
        '已通过的检查见 ../../reports/validation.json；必要条件通过不证明可行。'
        '未运行 COPT/Gurobi，未验证目标程序读取，也没有基准解。\n', encoding='utf-8', newline='\n')
    return {'case_id': row['case_id'], 'source_case': row['source_case'], 'n_units': len(ids), 'horizon': 24,
            'classification': 'derived_model_changed', 'path': 'cases/' + row['case_id'],
            'max_cost_change_per_unit_hour': max(f['max_abs_cost_delta_per_hour'] for f in fits),
            'solve_status': 'not_run'}


def main():
    manifest = load(ROOT / 'pilot_manifest.json')
    catalog = [convert(row) for row in manifest['cases']]
    write(ROOT / 'catalog.json', {'profile': PROFILE, 'case_count': len(catalog), 'cases': catalog})
    print(json.dumps(catalog, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

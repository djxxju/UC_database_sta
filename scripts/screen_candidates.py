"""Optional source screening. Reads the supplied originals; never changes them."""
import argparse
import gzip
import json
from validate import ROOT, capacity_upper_screen, sha
from build_pilot import write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=__import__('pathlib').Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'pilot_manifest.json').read_text(encoding='utf-8'))
    chosen = {r['source_case'].split('/')[-1] for r in manifest['cases']}
    rows = []
    for path in sorted(args.source_dir.glob('*.json.gz')):
        d = json.loads(gzip.decompress(path.read_bytes()))
        generators = list(d['Generators'].values())
        if len(generators) > 20:
            continue
        u = {'horizon': d['Parameters']['Time (h)'], 'n_units': len(generators),
             'base_load': next(iter(d['Buses'].values()))['Load (MW)']}
        mapping = {'ramp_up': 'Ramp up limit (MW)', 'min_down': 'Minimum downtime (h)',
                   'initial_duration': 'Initial status (h)', 'initial_output': 'Initial power (MW)'}
        for dest, source in mapping.items():
            u[dest] = [g[source] for g in generators]
        u['pmin'] = [g['Production cost curve (MW)'][0] for g in generators]
        u['pmax'] = [g['Production cost curve (MW)'][-1] for g in generators]
        u['pstart'] = list(u['pmax'])
        name = path.name.removesuffix('.json.gz')
        rows.append({'source_case': 'or-lib/' + name, 'sha256': sha(path), 'n_units': len(generators),
                     'selected': name in chosen, 'screen': capacity_upper_screen(u),
                     'source_solve_status': 'not_run', 'target_solve_status': 'not_run'})
    write(ROOT / 'reports' / 'candidate_screening.json', {
        'policy': 'Screen source OR-LIB cases of at most 20 units; select two passing candidates without changing data.',
        'limitation': 'Conditional on documented target startup-ramp interpretation; not an original-model infeasibility claim.',
        'candidate_count': len(rows), 'cases': rows})
    print(json.dumps({'candidates': len(rows), 'selected': sum(r['selected'] for r in rows)}))


if __name__ == '__main__':
    main()

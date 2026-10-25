#!/usr/bin/env python3
"""Run independent browser suites concurrently without reducing their coverage."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'build/browser-acceptance'


def command(script, *args, **env):
    return {'argv': ['python' if script.endswith('.py') else 'node', 'tests/' + script, *args], 'env': env}


def groups():
    return {
        'navigation': [
            command('runtime_paths.cjs', '_site', '/site'),
            command('runtime_paths.cjs', 'build/production', '/'),
            command('runtime_paths.cjs', 'build/qa-navigation/custom', '/qa-preview'),
            *[command(name + '.cjs') for name in ['navigation', 'browser_smoke', 'business-maps', 'preview-guard', 'environment', 'portable_deploy']],
        ],
        'layout-and-models': [
            *[command(name + '.cjs') for name in ['fault_lookup', 'frontend_events', 'ticket_modal_visual', 'page_visual_acceptance']],
            command('model_guidance.cjs', '_site', '/site'),
            command('district_matrix.cjs'), command('run_model_checks.py'), command('editorial_links.cjs'),
            command('model_directory.cjs'), command('home_entry_reviews.cjs', 'build/production'),
        ],
        'inventory-preview': [command('interactions.cjs',
            INTERACTION_MATRIX=json.dumps([{'label': 'preview', 'directory': str(ROOT / '_site'), 'base': '/site'}]),
            INTERACTION_OUTPUT=str(ROOT / 'build/qa-interactions/preview'))],
        'inventory-production': [command('interactions.cjs',
            INTERACTION_MATRIX=json.dumps([{'label': 'production', 'directory': str(ROOT / 'build/production'), 'base': ''}]),
            INTERACTION_OUTPUT=str(ROOT / 'build/qa-interactions/production'))],
        'backend-journeys': [
            command('interactions.cjs', INTERACTION_EXTRAS_ONLY='1', INTERACTION_OUTPUT='build/qa-interactions-extras'),
            command('backend_browser.cjs', 'build/production'), command('owner_browser.cjs', 'build/production'),
            command('priority_service.cjs'), command('priority_http.cjs', 'build/production'),
            command('priority_preview.cjs', '_site', '/site'), command('service_operations_browser.cjs', 'build/production'),
        ],
    }


def run_group(name, commands):
    rows = []
    for index, spec in enumerate(commands):
        log = OUTPUT / f'{name}-{index:02d}.log'
        started = time.monotonic()
        with log.open('w') as stream:
            result = subprocess.run(spec['argv'], cwd=ROOT, env=dict(os.environ, **spec['env']), stdout=stream, stderr=subprocess.STDOUT)
        row = dict(spec, exit_code=result.returncode, seconds=round(time.monotonic() - started, 2), log=str(log.relative_to(ROOT)))
        rows.append(row)
        print(json.dumps({'group': name, 'argv': spec['argv'], 'passed': result.returncode == 0, 'seconds': row['seconds']}), flush=True)
        if result.returncode:
            print(log.read_text(errors='replace')[-18000:], flush=True)
            break
    return {'group': name, 'passed': len(rows) == len(commands) and all(row['exit_code'] == 0 for row in rows), 'commands': rows}


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    subprocess.run(['python', 'scripts/build_site.py', '--mode', 'preview', '--output', 'build/qa-navigation/custom', '--base-path', '/qa-preview'], cwd=ROOT, check=True)
    subprocess.run(['python', 'scripts/check_site.py', 'build/qa-navigation/custom', '--mode', 'preview', '--base-path', '/qa-preview', '--report', 'build/custom-check.json'], cwd=ROOT, check=True)
    suites = groups()
    reports = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(run_group, name, commands) for name, commands in suites.items()]
        for future in as_completed(futures):
            reports.append(future.result())
    inventory = []
    for mode in ['preview', 'production']:
        path = ROOT / f'build/qa-interactions/{mode}/interactions-final.json'
        if path.is_file():
            inventory.extend(json.loads(path.read_text())['reports'])
    inventory_passed = len(inventory) == 2 and all(row['passed'] for row in inventory)
    (ROOT / 'build/qa-interactions').mkdir(parents=True, exist_ok=True)
    (ROOT / 'build/qa-interactions/interactions-final.json').write_text(json.dumps({'passed': inventory_passed, 'inventory_only': False, 'reports': inventory}, ensure_ascii=False, indent=2) + '\n')
    passed = len(reports) == len(suites) and all(row['passed'] for row in reports) and inventory_passed
    report = {'passed': passed, 'parallel_groups': 4, 'all_suites_required': True, 'groups': sorted(reports, key=lambda row: row['group'])}
    (ROOT / 'build/browser-acceptance-run.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': passed, 'groups': len(reports), 'commands': sum(len(row['commands']) for row in reports)}), flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())

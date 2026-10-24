#!/usr/bin/env python3
"""Run real-browser model journeys against an isolated root-mounted preview."""
from __future__ import annotations
import functools
import http.server
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def main() -> None:
    output = ROOT / 'build/qa-model'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='saglam-model-checks-') as temporary:
        build = subprocess.run(
            ['python', 'scripts/build_site.py', '--mode', 'preview', '--output', temporary, '--base-path', '/'],
            cwd=ROOT, check=True, capture_output=True, text=True)
        (output / 'build-info.json').write_text(build.stdout, encoding='utf-8')
        handler = functools.partial(QuietHandler, directory=temporary)
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        env = dict(os.environ, ST_TEST_ORIGIN=f'http://127.0.0.1:{server.server_port}',
                   ST_TEST_RESULT=str(output / 'model-ux.json'))
        results = []
        try:
            for script, report in [('brand_registry.cjs', 'brand-registry.json'), ('model_ux.cjs', 'model-ux.json')]:
                result = subprocess.run(['node', str(ROOT / 'tests' / script)], cwd=ROOT, env=env,
                                        capture_output=True, text=True, timeout=180)
                if result.returncode:
                    raise RuntimeError(script + '\n' + result.stdout + '\n' + result.stderr)
                data = json.loads(result.stdout)
                (output / report).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                results.append({'test': script, 'checks': len(data.get('checks', [])), 'passed': True})
        finally:
            server.shutdown()
            server.server_close()
        print(json.dumps({'passed': True, 'tests': results, 'production_requests': 0}, ensure_ascii=False))


if __name__ == '__main__':
    main()

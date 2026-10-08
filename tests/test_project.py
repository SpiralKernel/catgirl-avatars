import base64
import copy
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('catgirl_generator', ROOT / 'generate.py')
art = importlib.util.module_from_spec(spec)
spec.loader.exec_module(art)
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aRZkAAAAASUVORK5CYII=')


def definitions_for(graph):
    result = {}
    for node in graph.values():
        required = {}
        for name, value in node['inputs'].items():
            if art.is_link(value, graph):
                continue
            required[name] = ['STRING'] if name == 'text' else ([[value]] if isinstance(value, str) else ['INT'])
        result[node['class_type']] = {'input': {'required': required}}
    return result


class Recipes(unittest.TestCase):
    def test_every_recipe_has_one_matching_sample_and_checksum(self):
        assets = json.loads((ROOT / 'catalog.json').read_text())['assets']
        self.assertEqual({a['variant'] for a in assets}, set(art.VARIANTS))
        self.assertEqual(len(assets), len(art.VARIANTS))
        for asset in assets:
            with self.subTest(asset['variant']):
                path = ROOT / asset['path']
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), asset['sha256'])
                self.assertEqual(asset['dimensions'], [1536, 1536])
                self.assertEqual(asset['path'], art.VARIANTS[asset['variant']]['image'])

    def test_all_graphs_are_connected_text_to_image(self):
        for name in art.VARIANTS:
            with self.subTest(name):
                graph, _ = art.build(name)
                reachable = set()

                def visit(key, stack):
                    self.assertNotIn(key, stack, 'cycle')
                    if key in reachable:
                        return
                    reachable.add(key)
                    for value in graph[key]['inputs'].values():
                        if isinstance(value, list):
                            self.assertTrue(art.is_link(value, graph))
                            visit(value[0], stack | {key})
                visit(art.VARIANTS[name]['final_node'], set())
                self.assertEqual(reachable, set(graph))
                self.assertEqual(sum(n['class_type'] == 'SaveImage' for n in graph.values()), 1)
                self.assertFalse(any(n['class_type'].startswith('LoadImage') for n in graph.values()))
                self.assertEqual(graph['6']['inputs']['width'], 1024)
                self.assertEqual(graph['12']['inputs']['width'], 1536)

    def test_ui_widgets_and_links_match_api_graph_for_every_recipe(self):
        for name in art.VARIANTS:
            graph, ui = art.build(name)
            links = {link[0]: link for link in ui['links']}
            for node in ui['nodes']:
                key = str(node['id'])
                if key not in graph:
                    self.assertEqual(node['type'], 'Note')
                    continue
                with self.subTest(recipe=name, node=key):
                    self.assertEqual(node['type'], graph[key]['class_type'])
                    fields = art.WIDGETS[node['type']]
                    expected = [graph[key]['inputs'][field] if field else 'fixed' for field in fields]
                    self.assertEqual(node['widgets_values'], expected)
                    for inp in node.get('inputs', []):
                        if inp.get('link') is not None:
                            link = links[inp['link']]
                            self.assertEqual(graph[key]['inputs'][inp['name']], [str(link[1]), link[2]])

    def test_default_ui_is_ready_without_export(self):
        _, built = art.build('lingyin/01_closed_smile')
        stored = json.loads((ROOT / 'workflows/anima-avatar-hd.workflow.json').read_text())
        self.assertEqual(built, stored)
        upscaler = next(n for n in stored['nodes'] if n['type'] == 'UpscaleModelLoader')
        self.assertEqual(upscaler['widgets_values'], ['4x-NMKD-UltraYandere-Lite.pth'])

    def test_seed_override_reaches_both_stages_without_mutating_defaults(self):
        before = copy.deepcopy(art.TEMPLATE), copy.deepcopy(art.VARIANTS)
        graph, _ = art.build('random-cat-avatars/01_mint', 123)
        self.assertEqual([graph[k]['inputs']['seed'] for k in ('7', '14')], [123, 123])
        self.assertEqual(before, (art.TEMPLATE, art.VARIANTS))

    def test_model_overrides_reach_ui(self):
        graph, ui = art.build('lingyin/03_wink', models={'unet_name': 'subfolder/base.safetensors'})
        self.assertEqual(graph['1']['inputs']['unet_name'], 'subfolder/base.safetensors')
        self.assertEqual(next(n for n in ui['nodes'] if n['id'] == 1)['widgets_values'][0], 'subfolder/base.safetensors')

    def test_explicit_models_reject_typo(self):
        self.assertEqual(art.parse_models(['vae_name=foo.safetensors']), {'vae_name': 'foo.safetensors'})
        for text in ('vae=foo', 'vae_name=', 'no-separator'):
            with self.assertRaises(ValueError):
                art.parse_models([text])

    def test_local_filename_alias_and_missing_model(self):
        graph, _ = art.build('lingyin/03_wink')
        definitions = definitions_for(graph)
        definitions['UNETLoader']['input']['required']['unet_name'] = [['anima_baseV10.safetensors']]
        self.assertEqual(art.validate_graph(graph, definitions)['1']['inputs']['unet_name'], 'anima_baseV10.safetensors')
        definitions['UNETLoader']['input']['required']['unet_name'] = [[]]
        with self.assertRaisesRegex(ValueError, 'unet_name'):
            art.validate_graph(graph, definitions)

    def test_missing_node_is_reported(self):
        graph, _ = art.build('lingyin/03_wink')
        definitions = definitions_for(graph)
        del definitions['UNETLoader']
        with self.assertRaisesRegex(ValueError, 'missing node UNETLoader'):
            art.validate_graph(graph, definitions)

    def test_image_download_uses_view_and_never_overwrites(self):
        routes = []

        def fetch(route, data=None, binary=False):
            routes.append(route)
            self.assertTrue(binary)
            return PNG
        with tempfile.TemporaryDirectory() as temp:
            wanted = Path(temp) / 'avatar.png'
            wanted.write_bytes(b'keep me')
            actual = art.save_output(fetch, {'filename': 'test image.png', 'subfolder': 'a/b'}, wanted)
            self.assertNotEqual(wanted, actual)
            self.assertEqual(wanted.read_bytes(), b'keep me')
            self.assertEqual(actual.read_bytes(), PNG)
            self.assertIn('filename=test+image.png', routes[0])
            self.assertIn('subfolder=a%2Fb', routes[0])

    def test_invalid_image_is_not_written(self):
        with tempfile.TemporaryDirectory() as temp:
            wanted = Path(temp) / 'avatar.png'
            with self.assertRaisesRegex(RuntimeError, 'non-PNG'):
                art.save_output(lambda *a, **kw: b'<html>error</html>', {'filename': 'x.png'}, wanted)
            self.assertFalse(wanted.exists())

    def test_run_submits_resolved_ui_and_downloads_final_output(self):
        graph, _ = art.build('lingyin/03_wink', seed=456)
        calls = []

        def fetch(route, data=None, binary=False):
            calls.append((route, data))
            if route == '/prompt':
                self.assertEqual(data['prompt']['7']['inputs']['seed'], 456)
                self.assertEqual(data['extra_data']['extra_pnginfo']['workflow'], art.to_ui(data['prompt'], 'lingyin/03_wink'))
                return {'prompt_id': 'pid'}
            if route == '/history/pid':
                return {'pid': {'status': {'status_str': 'success'},
                                'outputs': {'16': {'images': [{'filename': 'output.png', 'type': 'output'}]}}}}
            if route.startswith('/view?'):
                return PNG
            self.fail(route)
        with tempfile.TemporaryDirectory() as temp:
            paths = art.run(fetch, 'lingyin/03_wink', graph, Path(temp), 30)
            self.assertEqual(paths[0].read_bytes(), PNG)
            self.assertEqual(paths[0].relative_to(temp).as_posix(), 'lingyin/03_wink.png')
        self.assertEqual(graph['16']['inputs']['filename_prefix'], 'catgirl-avatars/lingyin/03_wink')

    def test_server_generation_errors_do_not_save(self):
        def fetch(route, data=None, binary=False):
            if route == '/prompt':
                return {'prompt_id': 'failed'}
            return {'failed': {'status': {'status_str': 'error', 'messages': ['out of memory']}}}
        graph, _ = art.build('lingyin/03_wink')
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(RuntimeError, 'out of memory'):
                art.run(fetch, 'lingyin/03_wink', graph, Path(temp), 30)
            self.assertFalse(list(Path(temp).rglob('*.png')))

    def test_timeout_keeps_server_task_id(self):
        def fetch(route, data=None, binary=False):
            return {'prompt_id': 'still-running'} if route == '/prompt' else {}
        graph, _ = art.build('lingyin/03_wink')
        with tempfile.TemporaryDirectory() as temp, patch.object(art.time, 'monotonic', side_effect=[0, 31]):
            with self.assertRaisesRegex(TimeoutError, 'still-running'):
                art.run(fetch, 'lingyin/03_wink', graph, Path(temp), 30)

    def test_cli_exports_both_formats_offline(self):
        with tempfile.TemporaryDirectory() as temp:
            for fmt in ('ui', 'api'):
                path = Path(temp) / (fmt + '.json')
                result = subprocess.run([sys.executable, str(ROOT / 'generate.py'), 'export',
                                         'calico/02_wink', '--format', fmt, '--seed', '789', '--out', str(path)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                data = json.loads(path.read_text())
                if fmt == 'api':
                    self.assertEqual(data['7']['inputs']['seed'], 789)
                else:
                    self.assertEqual(next(n for n in data['nodes'] if n['id'] == 7)['widgets_values'][0], 789)
            result = subprocess.run([sys.executable, str(ROOT / 'generate.py'), 'export',
                                     'calico/02_wink', '--out', str(path)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)

    def test_readme_and_docs_local_links_exist(self):
        for doc in list((ROOT / 'docs').glob('*.md')) + list(ROOT.glob('*.md')):
            text = doc.read_text()
            links = re.findall(r'\]\(([^)\s]+)\)', text) + re.findall(r'src="([^"]+)"', text)
            for link in links:
                if '://' not in link and not link.startswith('#'):
                    with self.subTest(doc=doc.name, link=link):
                        self.assertTrue((doc.parent / link.split('#')[0]).exists())

    def test_no_absolute_home_paths_or_model_weights(self):
        for path in ROOT.rglob('*'):
            if not path.is_file() or '.git' in path.parts or '__pycache__' in path.parts:
                continue
            self.assertNotIn(path.suffix, {'.safetensors', '.ckpt', '.pth', '.pt'})
            if path.suffix in ('.md', '.json') or path.name == 'generate.py':
                self.assertNotIn('/home/' + 'sink', path.read_text())


if __name__ == '__main__':
    unittest.main()

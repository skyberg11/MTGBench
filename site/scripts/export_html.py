"""Export the current site as one HTML file that also works via file://."""
import argparse
import base64
import json
import mimetypes
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / '.site-build'
OUTPUT = ROOT / 'dist/MTGBench-preview.html'


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f'Site entry point changed: expected exactly one {old!r}')
    return source.replace(old, new)


def inline_json(value):
    # A literal </script> in a translated string must not end the HTML script.
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')


def script(name):
    source = (BUILD / name).read_text(encoding='utf-8')
    source = re.sub(r'^import .*?;\n', '', source, flags=re.MULTILINE)
    return re.sub(r'^export ', '', source, flags=re.MULTILINE)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--single-line-title', action='store_true',
                        help='Use the alternate preview filename; the single-line desktop title is now standard')
    args = parser.parse_args()
    output = OUTPUT.with_name('MTGBench-preview-single-line.html') if args.single_line_title else OUTPUT
    subprocess.run([sys.executable, str(ROOT / 'site/scripts/build.py')], check=True)
    json_files = {name: json.loads((BUILD / name).read_text(encoding='utf-8'))
                  for name in ('data.json', 'research.json', 'config.json')}
    paths = [BUILD / 'summary.csv', BUILD / 'research.json']
    for directory in ('assets', 'cards'):
        paths.extend(path for path in sorted((BUILD / directory).rglob('*'))
                     if path.is_file() and path.suffix.lower() in {'.svg', '.png', '.jpg', '.jpeg', '.webp', '.pdf'})
    assets = {}
    for path in paths:
        assets[path.relative_to(BUILD).as_posix()] = {
            'type': mimetypes.guess_type(path.name)[0] or 'application/octet-stream',
            'base64': base64.b64encode(path.read_bytes()).decode('ascii'),
        }
    poster = json_files['config.json'].get('posterUrl')
    if poster and poster not in assets:
        raise ValueError('The portable HTML requires a local poster in site/assets')

    content = script('content.js')
    research = script('research.js')
    research = replace_once(research,
        "download.href=key==='overall'||key==='language'?'summary.csv':'research.json';download.download='';",
        "download.download=key==='overall'||key==='language'?'summary.csv':'research.json';download.href=bundleAsset(download.download);")
    app = script('app.js')
    app = replace_once(app, 'new URLSearchParams(location.search)',
                       "new URLSearchParams(location.search || 'ui=en&language=ru')")
    app = replace_once(app, 'function syncUrl() {',
                       "function syncUrl() { if(location.protocol==='file:')return;")
    app = replace_once(app, 'img.src=`assets/logos/${family}.svg`;',
                       'img.src=bundleAsset(`assets/logos/${family}.svg`);')
    app = replace_once(app, 'a.href=config.posterUrl;', 'a.href=bundleAsset(config.posterUrl);')
    app = replace_once(app, 'img.src=config.posterUrl;', 'img.src=bundleAsset(config.posterUrl);')
    if app.count('fetch(') != 2:
        raise ValueError('Site data loading changed; update the portable data adapter')
    app = app.replace('fetch(', 'readBundle(')

    adapter = """
const assetCache=new Map();
function bundleAsset(path){
 if(!assetCache.has(path)){
  const entry=bundledAssets[path];
  if(!entry)throw new Error('Missing bundled asset: '+path);
  const bytes=Uint8Array.from(atob(entry.base64),character=>character.charCodeAt(0));
  assetCache.set(path,URL.createObjectURL(new Blob([bytes],{type:entry.type})));
 }
 return assetCache.get(path);
}
async function readBundle(path){
 if(!(path in bundledJson))throw new Error('Missing bundled data: '+path);
 return {ok:true,json:async()=>bundledJson[path]};
}
"""
    asset_setup = """
for(const game of Object.keys(cardFiles))cardFiles[game]=bundleAsset(cardFiles[game]);
for(const node of document.querySelectorAll('[data-bundle-src]'))node.src=bundleAsset(node.dataset.bundleSrc);
for(const node of document.querySelectorAll('[data-bundle-href]'))node.href=bundleAsset(node.dataset.bundleHref);
"""
    javascript = '\n'.join([
        "'use strict';\n(()=>{",
        'const bundledJson=' + inline_json(json_files) + ';',
        'const bundledAssets=' + inline_json(assets) + ';',
        adapter, content, asset_setup, research, app, '})();',
    ])
    if re.search(r'</script', javascript, flags=re.IGNORECASE):
        raise ValueError('Unexpected closing script tag in source')
    html = (BUILD / 'index.html').read_text(encoding='utf-8')
    html = replace_once(html,
        '<link rel="stylesheet" href="style.css"><script type="module" src="app.js"></script>',
        '<style>\n' + (BUILD / 'style.css').read_text(encoding='utf-8') + '\n</style>')
    html = re.sub(r'src="((?:assets|cards)/[^"]+)"', r'data-bundle-src="\1"', html)
    html = html.replace('href="summary.csv"', 'data-bundle-href="summary.csv"')
    html = html.replace('id="raw-data" download', 'id="raw-data" download="summary.csv"')
    html = html.replace('href="./"', 'href="#main"')
    html = replace_once(html, '</body>', '<script>\n' + javascript + '\n</script>\n</body>')
    output.parent.mkdir(exist_ok=True)
    output.write_text(html, encoding='utf-8')
    print(f'Exported {output} ({output.stat().st_size / 1024 / 1024:.2f} MiB)')


if __name__ == '__main__':
    main()

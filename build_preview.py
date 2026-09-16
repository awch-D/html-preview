from pathlib import Path
import base64
import json
import mimetypes
import re
import subprocess

root = Path(__file__).resolve().parent
assets = {}
for path in (root / 'assets').rglob('*'):
    if path.suffix in {'.svg', '.jpg', '.png', '.webp'}:
        mime = mimetypes.guess_type(str(path))[0]
        assets[path.relative_to(root).as_posix()] = 'data:' + mime + ';base64,' + base64.b64encode(path.read_bytes()).decode()

pages = {}
for name in ('a', 'b', 'c'):
    path = root / f'design-{name}.html'
    source = path.read_text()
    navigation = '''<script>document.addEventListener('click',function(event){const link=event.target.closest('a[href^="#"]');if(!link)return;const target=document.getElementById(link.getAttribute('href').slice(1));if(target){event.preventDefault();target.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});}});</script>'''
    source = source.replace('</body>', navigation + '</body>')
    for index, script in enumerate(re.findall(r'<script\b[^>]*>(.*?)</script>', source, re.S | re.I)):
        result = subprocess.run(['node', '--check'], input=script, text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError(f'{path.name} script {index}: {result.stderr}')
    for local, data in assets.items():
        source = source.replace(local, data)
    missing = re.findall(r'assets/[^\s\"\x27<>)]*', source)
    if missing:
        raise RuntimeError(f'{path.name}: missing assets {missing}')
    pages[name] = source

shell = (root / 'comparison.html').read_text()
serialized = json.dumps(pages, ensure_ascii=False).replace('<', '\\u003c')
output = shell.replace('__PAGES__', serialized)
for index, script in enumerate(re.findall(r'<script\b[^>]*>(.*?)</script>', output, re.S | re.I)):
    result = subprocess.run(['node', '--check'], input=script, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f'index.html script {index}: {result.stderr}')
(root / 'index.html').write_text(output)
print(f'Built index.html: {len(output.encode()):,} bytes; 3 embedded designs; {len(assets)} embedded assets.')
print('All inline scripts passed node --check. The final HTML has no external asset dependency.')

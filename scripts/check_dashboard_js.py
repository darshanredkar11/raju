import re
import subprocess
import tempfile
from pathlib import Path

html=Path('sanjay_pilot/dashboard.html').read_text(encoding='utf-8')
scripts=re.findall(r'<script>(.*?)</script>',html,flags=re.DOTALL)
if len(scripts)!=1:
    raise SystemExit(f'Expected one inline dashboard script, found {len(scripts)}')
with tempfile.NamedTemporaryFile(mode='w',suffix='.js',encoding='utf-8') as f:
    f.write(scripts[0]); f.flush()
    subprocess.run(['node','--check',f.name],check=True)
print('Dashboard JavaScript syntax OK')

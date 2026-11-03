#!/usr/bin/env python3
"""Read back critical public files, allowing a bounded Pages CDN propagation lag."""
from pathlib import Path
import argparse,hashlib,time,urllib.request,urllib.error

parser=argparse.ArgumentParser()
parser.add_argument('--dist',type=Path,required=True)
parser.add_argument('--url',required=True)
args=parser.parse_args()
names=['index.html','tcg-modern-index.html','top-50.html','catalogue.js','market-history.js',
       'market-release.json','top50-data.js','top50-release.json','refresh-status.json','refresh-status.js']
pending={n:hashlib.sha256((args.dist/n).read_bytes()).hexdigest() for n in names}
for attempt in range(9):
    for name,expected in list(pending.items()):
        try:
            req=urllib.request.Request(args.url.rstrip('/')+'/'+name+'?release-check='+expected[:16],headers={'User-Agent':'BuyTrigger.Cards release verification/1.1','Cache-Control':'no-cache'})
            with urllib.request.urlopen(req,timeout=20) as r: actual=hashlib.sha256(r.read()).hexdigest()
            if actual==expected:del pending[name]
        except (urllib.error.URLError,TimeoutError):pass
    if not pending:break
    if attempt<8:time.sleep(10)
if pending:raise SystemExit('Live verification mismatch: '+', '.join(pending))
print('PASS: all 10 critical live files match the verified artifact.')

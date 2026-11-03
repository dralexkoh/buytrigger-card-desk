#!/usr/bin/env python3
"""Commit only the reviewed pipeline outputs; never stage unrelated work."""
from pathlib import Path
import argparse,json,subprocess


def git(*args,check=True):
    return subprocess.run(['git',*args],check=check,text=True,capture_output=True)


parser=argparse.ArgumentParser()
parser.add_argument('--receipt',type=Path,required=True)
args=parser.parse_args()
receipt=json.loads(args.receipt.read_text())
allowed={'catalogue.js','market-history.js','market-release.json','market-sources.json',
         'top50-data.js','top50-release.json','top50-sources.json','refresh-status.json'}
paths=receipt['promotedPaths']
for name in paths:
    p=Path(name)
    if p.is_absolute() or '..' in p.parts or not (name in allowed or name.startswith('data/refresh/') and p.suffix=='.json'):
        raise SystemExit('Unexpected pipeline commit path')
git('fetch','origin','main')
if git('rev-parse','HEAD').stdout!=git('rev-parse','origin/main').stdout:
    raise SystemExit('Remote main advanced; no data commit or deployment made. Rerun from current main.')
if git('diff','--cached','--name-only').stdout.strip():
    raise SystemExit('Unexpected pre-staged files')
git('add','--',*paths)
if not git('diff','--cached','--name-only').stdout.strip():
    print('No public refresh changes to commit.')
else:
    git('config','user.name','BuyTrigger Cards updater')
    git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    git('commit','-m','Update public Raw status and observations')
    git('push','origin','HEAD:main')
    print('Committed validated public refresh outputs.')

#!/usr/bin/env python3
"""Commit only the reviewed pipeline outputs; never stage unrelated work."""
from pathlib import Path
import argparse,json,subprocess


def git(*args,check=True):
    return subprocess.run(['git',*args],check=check,text=True,capture_output=True)


ALLOWED={'catalogue.js','market-history.js','market-release.json','market-sources.json',
         'top50-data.js','top50-release.json','top50-sources.json','refresh-status.json','data/market-cache/thirtieth-current.json',
         'bluechip-collection-data.js','bluechip-collection-sources.json'}


def promoted_path_allowed(name, allowed=ALLOWED):
    p=Path(name)
    index_cache=len(p.parts)==3 and p.parts[:2]==('data','market-cache') and p.name.endswith('-current.json')
    return not (p.is_absolute() or '..' in p.parts or not (name in allowed or index_cache or name.startswith('data/refresh/') and p.suffix=='.json'))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--receipt',type=Path,required=True)
    args=parser.parse_args()
    receipt=json.loads(args.receipt.read_text())
    paths=receipt['promotedPaths']
    for name in paths:
        if not promoted_path_allowed(name):
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


if __name__=='__main__':
    main()

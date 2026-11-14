#!/usr/bin/env python3
"""Validate an isolated public refresh before promoting an explicit file list.

The caller owns git/deployment. Failed ingestion can publish only a failure
notice and immutable review receipts, while retaining every verified price.
"""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

from daily_refresh import COLLECTION_FILES, FILES


def execute(argv, cwd):
    subprocess.run(argv, cwd=cwd, check=True)


def copy_source(source, stage):
    stage.mkdir()
    for p in source.iterdir():
        if p.is_symlink():
            raise ValueError('Symlink in public source')
        if p.is_file() and (p.suffix in {'.html', '.css', '.js', '.json'} or p.name in {'requirements.txt', '.nojekyll', 'CNAME'}):
            shutil.copy2(p, stage/p.name)
    for name in ('assets', 'scripts', 'data'):
        if (source/name).exists():
            shutil.copytree(source/name, stage/name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))


def copy_one(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def apply_output(output, stage, failed):
    selected = ['refresh-status.json'] if failed else [*FILES, 'refresh-status.json']
    if not failed and (output / COLLECTION_FILES[0]).exists():
        selected.extend(COLLECTION_FILES)
    for name in selected:
        copy_one(output/name, stage/name)
    if failed:
        # Same-date provider revisions must survive temporary CI artifacts.
        for p in sorted((output/'data/refresh/review').glob('revision-*.json')):
            destination = stage/p.relative_to(output)
            if destination.exists() and destination.read_bytes()!=p.read_bytes():
                raise ValueError('Attempt to overwrite immutable revision receipt')
            copy_one(p,destination)
            selected.append(str(p.relative_to(output)))
    elif (output/'data/refresh').exists():
        for p in sorted((output/'data/refresh').rglob('*.json')):
            copy_one(p,stage/p.relative_to(output))
            selected.append(str(p.relative_to(output)))
    shared = output/'data/market-cache/thirtieth-current.json'
    if not failed and shared.exists():
        copy_one(shared, stage/'data/market-cache/thirtieth-current.json')
        selected.append('data/market-cache/thirtieth-current.json')
    if not failed and (stage/'data/market-rosters').exists():
        # Per-index caches for the shared Cards DB; rebuilt from the observations
        # this run already collected (no extra fetch). Approved rosters only.
        from index_cache import write_all
        selected.extend(write_all(stage))
    return selected


def run(args):
    source=args.site_dir.resolve()
    destination=args.dist_out.resolve()
    if destination==source or source.is_relative_to(destination) or destination.is_relative_to(source):
        raise ValueError('Distribution output must be outside public source')
    with tempfile.TemporaryDirectory(prefix='buytrigger-public-pipeline-') as temporary:
        workspace=Path(temporary); stage=workspace/'site'; output=workspace/'refresh'
        copy_source(source,stage)
        command=[sys.executable,str(source/'scripts/daily_refresh.py'),'--site-dir',str(source),
                 '--output-dir',str(output),'--cache-dir',str(args.cache_dir.resolve()),'--run-kind',args.run_kind]
        if args.activate: command.append('--activate')
        if args.fixture_dir: command+=['--fixture-dir',str(args.fixture_dir.resolve())]
        if args.now: command+=['--now',args.now]
        result=subprocess.run(command,cwd=source)
        if not (output/'refresh-status.json').is_file():
            raise ValueError('Collector failed before producing a safe status record')
        failed=result.returncode!=0
        selected=apply_output(output,stage,failed)
        execute(['npm','test'],stage)
        execute(['npm','run','typecheck'],stage)
        execute(['npm','run','build'],stage)
        execute(['npm','run','check:artifact'],stage)
        if destination.exists(): shutil.rmtree(destination)
        shutil.copytree(stage/'dist',destination)
        # Promotion is strictly after all validation; no broad workspace copy.
        for name in selected: copy_one(stage/name,source/name)
        status=json.loads((stage/'refresh-status.json').read_text())
        receipt={'schemaVersion':1,'sourceFailed':failed,'sourceDate':status['sourceDate'],
                 'status':status['status'],'dataReleaseId':status.get('dataReleaseId'),
                 'promotedPaths':selected,'checks':'passed','distributionFiles':sum(p.is_file() for p in destination.rglob('*'))}
        args.receipt.parent.mkdir(parents=True,exist_ok=True)
        args.receipt.write_text(json.dumps(receipt,indent=2)+'\n')
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'],'a') as f:
                f.write('source_failed='+str(failed).lower()+'\n')
        print(json.dumps({k:v for k,v in receipt.items() if k!='promotedPaths'},sort_keys=True))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--site-dir',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--dist-out',type=Path,required=True)
    parser.add_argument('--receipt',type=Path,required=True)
    parser.add_argument('--cache-dir',type=Path,required=True)
    parser.add_argument('--run-kind',choices=('manual','schedule'),default='manual')
    parser.add_argument('--activate',action='store_true')
    parser.add_argument('--fixture-dir',type=Path)
    parser.add_argument('--now')
    run(parser.parse_args())

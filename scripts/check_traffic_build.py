"""Review the built traffic integration and test the real artifact boundary.

Runs after npm run build. Each mutation is made in a disposable copy; it never
edits the reviewed dist or source. No browser or analytics endpoint is called.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from bs4 import BeautifulSoup
import argparse,json,os,shutil,subprocess

ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/'dist'
EXPECTED='https://brzawmbpwkdundruicca.supabase.co/functions/v1/cards-traffic-ingest'
config=json.loads((DIST/'analytics-config.json').read_text())
parser=argparse.ArgumentParser()
parser.add_argument('--expect-enabled',action='store_true',help='Use only after the lead enables the verified live backend and privacy configuration.')
args=parser.parse_args()
assert config['enabled'] is args.expect_enabled and config['privacyReviewed'] is args.expect_enabled
assert config['collectorEndpoint']==EXPECTED
documents=[p for p in DIST.rglob('*.html') if p.name!='404.html']
for path in documents:
 soup=BeautifulSoup(path.read_text(),'html.parser')
 tags=[t for t in soup.select('script[src]') if t['src'].split('?',1)[0]=='analytics.js']
 assert len(tags)==1 and tags[0].has_attr('defer'),str(path)
 assert '?v=' in tags[0]['src'],str(path)
 directory=[t for t in soup.select('script[src]') if t['src'].split('?',1)[0]=='tracking-catalogue.js']
 assert len(directory)==1 and directory[0].has_attr('defer') and '?v=' in directory[0]['src'],str(path)
assert not list(DIST.rglob('*traffic-preview*'))
cases=[
 ('another project endpoint',lambda folder:(folder/'analytics-config.json').write_text((folder/'analytics-config.json').read_text().replace('brzawmbpwkdundruicca','ukblxmvsqihnnyysvxes'))),
 ('private API URL in client',lambda folder:(folder/'analytics.js').write_text((folder/'analytics.js').read_text()+"\nconst forbidden='https://brzawmbpwkdundruicca.supabase.co/rest/v1/private';\n")),
 ('endpoint suffix must not inherit allowlist',lambda folder:(folder/'analytics.js').write_text((folder/'analytics.js').read_text()+"\nconst forbidden='"+EXPECTED+"/not-approved';\n")),
 ('unexpected config credential',lambda folder:(folder/'analytics-config.json').write_text(json.dumps({**config,'apikey':'not-allowed-even-if-public'}))),
 ('enabled without privacy approval',lambda folder:(folder/'analytics-config.json').write_text(json.dumps({**config,'enabled':True,'privacyReviewed':False}))),
 ('owner mockup in public artifact',lambda folder:(folder/'owner-traffic-preview.html').write_text('<title>Owner mockup</title>')),
]
for label,mutate in cases:
 with TemporaryDirectory(prefix='bt-traffic-artifact-') as temporary:
  target=Path(temporary)/'dist';shutil.copytree(DIST,target);mutate(target)
  result=subprocess.run(['python3',str(ROOT/'scripts/check_artifact.py')],env={**os.environ,'BT_CARD_DESK_ARTIFACT_DIR':str(target)},capture_output=True,text=True)
  assert result.returncode!=0,label
print(f'PASS: optional client on {len(documents)} built pages; {"enabled and privacy-reviewed" if args.expect_enabled else "disabled"} config; {len(cases)} forbidden artifact mutations rejected.')

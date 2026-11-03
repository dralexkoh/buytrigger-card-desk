#!/usr/bin/env python3
"""Read back critical public files, allowing a bounded Pages CDN propagation lag."""
from pathlib import Path
from urllib.parse import urlsplit
import argparse,hashlib,time,urllib.request,urllib.error

PRIMARY_URL='https://buytrigger.cards/'
NAMES=['assets/editorial-price-profit-v1.svg','assets/editorial-under20-v1.svg','assets/editorial-index-reader-v1.svg','stories/under20-upside/index.html','index-refinement.css', 'card-art.js', 'modern.js', 'top50.js', 'site.js', 'stories/how-the-index-works/index.html', 'homepage.css', 'typography.css', 'assets/editorial-grading-desk-v1.jpg', 'editorial.js', 'site.css', 'header.css', 'stories/psa-value-returns/index.html', 'index.html', 'tcg-modern-index.html', 'top-50.html', 'catalogue.js', 'market-history.js', 'market-release.json', 'top50-data.js', 'top50-release.json', 'refresh-status.json', 'refresh-status.js', 'social.js', 'analytics.js', 'analytics-config.json', 'sitemap.xml', 'rss.xml', 'robots.txt']


def verify(dist,url=PRIMARY_URL,attempts=9,delay=10):
    pending={n:hashlib.sha256((dist/n).read_bytes()).hexdigest() for n in NAMES}
    primary=urlsplit(PRIMARY_URL)
    for attempt in range(attempts):
        for name,expected in list(pending.items()):
            try:
                req=urllib.request.Request(url.rstrip('/')+'/'+name+'?release-check='+expected[:16],
                    headers={'User-Agent':'BuyTrigger.Cards release verification/1.3.0','Cache-Control':'no-cache'})
                with urllib.request.urlopen(req,timeout=20) as response:
                    final=urlsplit(response.geturl())
                    actual=hashlib.sha256(response.read()).hexdigest()
                # A legacy URL is a valid input only when it reaches the primary
                # HTTPS site. Matching bytes on an old host do not prove cutover.
                if (final.scheme,final.netloc)==(primary.scheme,primary.netloc) and actual==expected:
                    del pending[name]
            except (urllib.error.URLError,TimeoutError):pass
        if not pending:break
        if attempt<attempts-1:time.sleep(delay)
    return pending


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--dist',type=Path,required=True)
    parser.add_argument('--url',default=PRIMARY_URL)
    args=parser.parse_args()
    pending=verify(args.dist,args.url)
    if pending:raise SystemExit('Primary-domain live verification mismatch: '+', '.join(pending))
    print(f'PASS: all {len(NAMES)} critical live files match the verified artifact at {PRIMARY_URL}')


if __name__=='__main__':
    main()

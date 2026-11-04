#!/usr/bin/env python3
"""Read back critical public files, allowing a bounded Pages CDN propagation lag."""
from pathlib import Path
from urllib.parse import urlsplit
import argparse,hashlib,time,urllib.request,urllib.error

PRIMARY_URL='https://buytrigger.cards/'
NAMES=['commerce-data.js','commerce.js','commerce.css','refinement.css','drops.js','drops.html','assets/editorial-price-profit-v1.svg','assets/editorial-under20-v1.svg','assets/editorial-index-reader-v1.svg','stories/under20-upside/index.html','index-refinement.css', 'card-art.js', 'modern.js', 'top50.js', 'site.js', 'stories/how-the-index-works/index.html', 'homepage.css', 'typography.css', 'assets/editorial-grading-desk-v1.jpg', 'editorial.js', 'site.css', 'header.css', 'stories/psa-value-returns/index.html', 'index.html', 'tcg-modern-index.html', 'top-50.html', 'catalogue.js', 'market-history.js', 'market-release.json', 'top50-data.js', 'top50-release.json', 'refresh-status.json', 'refresh-status.js', 'social.js', 'analytics.js', 'analytics-config.json', 'sitemap.xml', 'rss.xml', 'robots.txt']

NAMES += ['article-authors.js','article-features.css'] + ['stories/'+slug+'/index.html' for slug in ['delta-reign-friday-uk-upc-release-check', 'psa-backlog-november-2026-collector-guide']] + ['assets/features-20261104/'+name for name in ['delta-announcement-heading.png', 'delta-pack-counts-mobile.png', 'delta-pack-counts.csv', 'delta-pack-counts.pdf', 'delta-pack-counts.png', 'delta-pack-counts.svg', 'grading-queue-hero.png', 'psa-backlog-mobile.png', 'psa-backlog.csv', 'psa-backlog.pdf', 'psa-backlog.png', 'psa-backlog.svg', 'psa-report-heading.png', 'psa-turnaround-mobile.png', 'psa-turnaround.csv', 'psa-turnaround.pdf', 'psa-turnaround.png', 'psa-turnaround.svg', 'release-calendar-hero.png', 'upc-pack-mix-mobile.png', 'upc-pack-mix.csv', 'upc-pack-mix.pdf', 'upc-pack-mix.png', 'upc-pack-mix.svg']]

NAMES += ['assets/features-20261104-visual-v3/delta-center-etb.webp', 'assets/features-20261104-visual-v3/delta-etb.webp', 'assets/features-20261104-visual-v3/psa-pikachu-queue.webp', 'assets/features-20261104-visual-v3/psa-value-announcement.webp', 'assets/features-20261104-visual-v3/release-queue-alex-oscar.webp', 'assets/features-20261104-visual-v3/upc-day-night.webp']
NAMES += ['assets/archive-refresh-20261104/santa-cruz-boards.webp', 'assets/archive-refresh-20261104/cover-profit.svg', 'assets/archive-refresh-20261104/cover-japan.webp', 'assets/archive-refresh-20261104/net-outcomes.png', 'assets/archive-refresh-20261104/cover-under20.webp', 'assets/archive-refresh-20261104/modern-interface.webp', 'assets/archive-refresh-20261104/santa-cruz-details.webp', 'assets/archive-refresh-20261104/pocket-letter.webp', 'assets/archive-refresh-20261104/cover-japan.svg', 'assets/archive-refresh-20261104/cover-under20.svg', 'assets/archive-refresh-20261104/cover-pocket.svg', 'assets/archive-refresh-20261104/modern-performance.webp', 'assets/archive-refresh-20261104/cover-index.svg', 'assets/archive-refresh-20261104/cover-safety.svg', 'assets/archive-refresh-20261104/cover-pocket.webp', 'assets/archive-refresh-20261104/cover-profit.webp', 'assets/archive-refresh-20261104/santa-cruz-overview.webp', 'assets/archive-refresh-20261104/cover-index.webp', 'assets/archive-refresh-20261104/net-outcomes.csv', 'assets/archive-refresh-20261104/net-outcomes-mobile.png', 'assets/archive-refresh-20261104/cover-safety.webp', 'stories/japanese-card-research/index.html', 'stories/psa-value-returns/index.html', 'stories/psa-october-theft-update/index.html', 'stories/delta-reign-product-guide-october/index.html', 'stories/pokemon-santa-cruz-card-art/index.html', 'stories/pocket-october-producer-letter/index.html', 'stories/welcome/index.html', 'stories/psa10-is-not-profit/index.html', 'stories/under20-upside/index.html', 'stories/how-the-index-works/index.html']
NAMES = list(dict.fromkeys(NAMES))

NAMES += ['market.html','30th-anniversary-index.html','shared-market.js','shared-market-engine.js','shared-market.css','shared-market-config.json','assets/30th-mewtwo-151-128.jpg']

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

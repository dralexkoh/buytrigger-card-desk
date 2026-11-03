"""Build the public Top 50 snapshot from explicitly supplied reviewed local inputs.

No network or database access. Incomplete source retrieval or artwork stops the build.
"""
from pathlib import Path
import argparse, hashlib, json, shutil

P=Path(__file__).resolve().parents[1]
def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,obj,prefix=None):
    s=json.dumps(obj,ensure_ascii=False,separators=(',',':') if prefix else None,indent=None if prefix else 2)
    if prefix:s=prefix+'='+s.replace('</','<\\/')+';'
    (P/name).write_text(s+'\n')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--review',required=True,type=Path);args=ap.parse_args();r=args.review.resolve()
    roster=read(r/'top50-membership.json');proof=read(r/'ranking-proof.json');h=read(r/'history/raw-history.json');im=read(r/'image-provenance.public.json');auctions=read(r/'auction-highlights.json');quality=read(r/'reviewed-holds.json')
    for e in quality['holds']:
        assert h['prices'][str(e['cardId'])][h['dates'].index(e['date'])]==e['reportedValue']
    h['exclusions']+=quality['holds']
    assert len({(e['cardId'],e['date']) for e in h['exclusions']})==len(h['exclusions'])
    frozen_sha=sha(r/'top50-membership.json')
    assert frozen_sha==proof['rosterSha256']==h['rosterSha256']==im['membershipSha256'],'Membership inputs disagree'
    assert len(roster)==50 and proof['unresolvedPositiveRowsAtOrAboveRank50']==0
    assert not h['missingRequestedArchives'] and h['availableArchiveCount']==h['requestedArchiveCount']==330,'Source retrieval incomplete'
    assert not im['failures'] and len(im['cards'])==50,'Artwork incomplete'
    assert 'pending' not in im['status'].lower(),'Final image review pending'
    images={c['key']:c for c in im['cards']};cards=[]
    for c in roster:
        i=images[f"{c['productId']}|{c['printing']}"]
        assert i['language']=='English' and i['pricedIdentity']['number']==c['number']
        for a in i['files'].values():
            src=r/'image-assets'/a['file'];dst=P/a['publicPath']
            assert sha(src)==a['sha256'] and a['unchangedDownload']
            assert dst.resolve().is_relative_to((P/'assets/top50').resolve())
            dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
        card={k:c[k] for k in ['id','rank','productId','groupId','name','number','set','printing','releaseDate','releaseDateBasis','rarity','language']}
        card.update({'image':i['files']['low']['publicPath'],'imageLarge':i['files']['high']['publicPath'],'imageProvider':i['imageProvider'],'imageSource':i['sourceMetadataURL'],'imageNote':i['imageNote'] or 'Reference scan: English catalogue issue.','imageExactPrinting':i['imageExactPrinting'],'imageAlt':i['alt'],'quotes':{'Raw':{'price':c['marketPrice'],'currency':'USD','date':c['priceDate'],'source':c['sourceURL'],'provider':'TCGplayer market via TCGCSV','method':'Exact product and printing; mixed-condition Raw USD guide, not a checked individual sale.'}}})
        count=sum(e['cardId']==c['id'] for e in h['exclusions'])
        if count:card['historyNote']=f'{count} source observation'+('s' if count!=1 else '')+' held; originals in Evidence.'
        caveat=next((v for v in quality['retainedCaveats'] if v['cardId']==c['id']),None)
        if caveat:card.update({'historyNote':'Sharp source-guide change retained; see Evidence.','historyCaveat':caveat['text']})
        cards.append(card)
    held={(e['cardId'],e['date']) for e in h['exclusions']}
    usable=lambda c,d,v:isinstance(v,(int,float)) and v>0 and (c['id'],d) not in held and (not c['releaseDate'] or d>=c['releaseDate'])
    full=[c['id'] for c in cards if all(usable(c,d,v) for d,v in zip(h['dates'],h['prices'][str(c['id'])]))]
    assert full,'No complete long-history basket: review required'
    observations=sum(usable(c,d,v) for c in cards for d,v in zip(h['dates'],h['prices'][str(c['id'])]))
    exclusions=[{'cardId':e['cardId'],'productId':e['productId'],'date':e['date'],'reportedValue':e['reportedValue'],'reason':e['reason'],'source':e['sourceURL']} for e in h['exclusions']]
    history={'dates':h['dates'],'prices':h['prices'],'archivePattern':'https://tcgcsv.com/archive/tcgplayer/prices-{date}.ppmd.7z','exclusions':exclusions,'cadence':h['cadence'],'cohorts':{'history':{'id':'bt-top50-raw-v1-complete-sampled-history','members':full},'current':{'id':'bt-top50-raw-v1-current50','members':[c['id'] for c in cards]}}}
    release={'version':'top50-raw-v1','published':'2026-11-03','sourceDate':proof['asOf'],'memberCount':50,'images':50,'exactPrintingImages':sum(c['imageExactPrinting'] for c in cards),'referenceImagesWithPrintingNote':sum(not c['imageExactPrinting'] for c in cards),'requestedHistoryStart':'2024-01-01','historyStart':h['dates'][0],'historyEnd':h['dates'][-1],'archiveCount':len(h['dates']),'incompleteArchiveDates':h['missingRequestedArchives'],'unsupportedInitialRange':h['unsupportedInitialRange'],'cadence':h['cadence'],'historyObservations':observations,'heldSourceObservations':len(exclusions),'longHistoryMembers':full,'automaticRefreshActive':False,'gradedStatus':'Pending; owner chose Raw first','universeSummary':f"Screened {proof['priceRowsScanned']:,} source rows across {proof['priceSource']['pokemonGroups']} Pokémon groups. The 50 highest eligible, matched English Raw guides are ranked here; there are no unresolved higher-priced rows in this defined universe. {proof['nullMarketPriceRows']} rows without market guides remain unranked. Ordinary staff and retail promos are included; named trophy/winner awards, placement awards, reproductions and sealed products are excluded. Sale frequency is not measured.",'rankingProof':{'priceRowsScanned':proof['priceRowsScanned'],'positivePriceRows':proof['positivePriceRows'],'nullMarketPriceRows':proof['nullMarketPriceRows'],'rank50CutoffUSD':proof['rank50CutoffUSD'],'unresolvedPositiveRowsAtOrAboveRank50':0,'method':proof['rankingMethod'],'definition':proof['definition'],'rosterSha256':frozen_sha,'priceArchiveSha256':proof['priceSource']['sha256']},'basis':'Current November 2026 ranking reconstructed retrospectively; complete-data subset introduces coverage-selection bias. Not a point-in-time Top 50, fund, executable offer or net return.'}
    # A mixed vintage/modern hero uses only genuinely matched-printing reference scans.
    preferred=[85927,84187,86903,183899,246723,183830]
    heroes=[next(c['id'] for c in cards if c['productId']==pid and c['imageExactPrinting']) for pid in preferred]
    data={'cards':cards,'history':history,'release':release,'heroIds':heroes,'auctions':auctions['events']}
    public_images={k:v for k,v in im.items() if k not in ['membershipSource','failures']}
    archives=[{k:v for k,v in a.items() if k!='path'} for d,a in sorted(h['archives'].items())]
    public_selection=[{k:c[k] for k in ['id','rank','productId','groupId','name','number','set','printing','releaseDate','releaseDateBasis','sourceURL','priceSourceURL']}|{'metadataSourceURL':c['metadataSource']['source_url'],'metadataSha256':c['metadataSource']['sha256']} for c in roster]
    sources={'source':'TCGplayer market via TCGCSV','sourceDate':proof['asOf'],'definition':proof['definition'],'rankingMethod':proof['rankingMethod'],'selection':public_selection,'rankingProof':release['rankingProof'],'excludedAboveCutoff':[{k:c.get(k) for k in ['groupId','productId','name','subTypeName','marketPrice','classification','classificationReason','productUrl']} for c in proof['excludedPositiveRowsAtOrAboveCutoff']],'archives':archives,'historySourceSha256':sha(r/'history/raw-history.json'),'qualityReviewSha256':sha(r/'reviewed-holds.json'),'cadence':h['cadence'],'unsupportedInitialRange':h['unsupportedInitialRange'],'heldObservations':exclusions,'retainedGuideCaveats':quality['retainedCaveats'],'auctionSourceNotes':{k:v for k,v in auctions.items() if k!='events'}}
    write('top50-data.js',data,'window.BT_TOP50');write('top50-release.json',release);write('top50-sources.json',sources);write('top50-image-sources.json',public_images)
    features=[{'image':cards[i-1]['image'],'alt':cards[i-1]['imageAlt']} for i in heroes]
    write('top50-feature.js',features,'window.BT_TOP50_FEATURES')
    print(json.dumps({'cards':50,'images':50,'archives':len(h['dates']),'completeHistoryMembers':len(full),'usableObservations':observations,'exactPrintingImages':release['exactPrintingImages'],'heroIds':heroes}))
if __name__=='__main__':main()

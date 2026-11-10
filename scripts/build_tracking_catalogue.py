"""Public article/link directory; rebuilt automatically for each publication."""
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import json,re

def create_catalogue(e):
 retailer_links={};source_hosts=set()
 for item in e['articles']:
  for source in item.get('sources',[]):
   u=urlparse(source['url'])
   if u.scheme=='https' and u.hostname:source_hosts.add(u.hostname)
  anchors=[a for section in item['sections'] for a in BeautifulSoup(section['html'],'html.parser').select('a[href]')]
  for source in item.get('sources',[]):
   anchor=BeautifulSoup('<a></a>','html.parser').a;anchor['href']=source['url'];anchor.string=source['label'];anchors.append(anchor)
  for anchor in anchors:
   u=urlparse(anchor['href'])
   if u.scheme!='https' or u.hostname not in ['www.amazon.co.uk','www.amazon.com']:continue
   match=re.fullmatch(r'/dp/([A-Z0-9]{10})',u.path)
   reviews=re.fullmatch(r'/portal/customer-reviews/([A-Z0-9]{10})',u.path)
   if not match and not reviews:raise ValueError('Amazon link needs an approved canonical product/review path: '+anchor['href'])
   asin=(match or reviews).group(1);kind='product' if match else 'reviews';market='uk' if u.hostname.endswith('.co.uk') else 'us'
   identity=f'amazon-{market}-{kind}-{asin}'
   entry=retailer_links.setdefault(identity,{'id':identity,'retailer':'amazon','host':u.hostname,'path':u.path,'kind':kind,'asin':asin,'label':anchor.get_text(' ',strip=True)[:160],'articles':[]})
   if item['slug'] not in entry['articles']:entry['articles'].append(item['slug'])
 traffic_catalogue={'version':1,'site':'buytrigger.cards','articles':[{'slug':a['slug'],'title':a['title']} for a in e['articles']],
  'news':[{'id':a['id'],'title':a['title']} for a in e.get('wire',[])],
  'pages':['/','/desk','/journal','/targets','/japan','/method','/funding','/privacy','/story-not-found','/tcg-modern-index','/top-50','/drops','/calculator','/market','/thirtieth','/advertise','/bluechip-archive'],
  'sourceHosts':sorted(source_hosts),'retailerLinks':list(retailer_links.values())}
 return traffic_catalogue

if __name__=='__main__':
 print(json.dumps(create_catalogue(json.loads((Path(__file__).resolve().parents[1]/'editorial.json').read_text())),ensure_ascii=False))

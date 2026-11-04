import copy
from datetime import datetime, timezone
import unittest
from drops_offers import validate_offers, ebay_link

class OfferContract(unittest.TestCase):
    def setUp(self):
        self.config={'schemaVersion':1,'placements':{'home':False,'drops':True},'ebay':{'enabled':True,'campaignId':'5339239680'},'amazonUk':{'enabled':False,'trackingId':'buytrigger-21'}}
        self.now=datetime(2026,11,4,17,0,tzinfo=timezone.utc)
        self.row={'id':'ebay-123456789012','productKey':'binder-test','title':'Binder test fixture','summary':'Synthetic test only. Never published.','region':'UK','country':'United Kingdom','language':'Not applicable','retailer':'eBay','seller':'Test seller','fulfilment':'Test UK delivery','event':'Available','availability':'In stock','productUrl':'https://www.ebay.co.uk/itm/123456789012','sourceUrl':'https://www.ebay.co.uk/itm/123456789012','checkedAt':'2026-11-04T16:59:00Z','expiresAt':'2026-11-04T17:14:00Z','affiliateProvider':'ebay','revision':1}
        self.row['affiliateUrl']=ebay_link(self.row['productUrl'],self.config,self.row['id'])
        self.data={'schemaVersion':1,'updatedAt':'2026-11-04T17:00:00Z','items':[self.row]}
    def test_fresh_offer_and_historical_build(self):
        self.assertTrue(validate_offers(self.data,self.config,self.now,True))
        later=datetime(2026,11,5,tzinfo=timezone.utc)
        self.assertTrue(validate_offers(self.data,self.config,later))
        with self.assertRaises(ValueError):validate_offers(self.data,self.config,later,True)
    def test_private_fields_duplicates_and_region_errors(self):
        for key,value in [('privateNotes','secret'),('country','Asia'),('sourceUrl','https://x.com/lead')]:
            data=copy.deepcopy(self.data);data['items'][0][key]=value
            with self.assertRaises(ValueError):validate_offers(data,self.config,self.now)
        self.data['items'].append(copy.deepcopy(self.row))
        with self.assertRaises(ValueError):validate_offers(self.data,self.config,self.now)
    def test_campaign_and_product_cannot_be_swapped(self):
        self.row['affiliateUrl']=self.row['affiliateUrl'].replace('5339239680','5330000000')
        with self.assertRaises(ValueError):validate_offers(self.data,self.config,self.now)
    def test_expiry_window_and_timezone_required(self):
        for key,value in [('checkedAt','2026-11-04T18:00:00Z'),('checkedAt','2026-11-04T16:59:00'),('expiresAt','2026-11-04T18:00:00Z')]:
            row=copy.deepcopy(self.row);row[key]=value
            with self.assertRaises(ValueError):validate_offers({**self.data,'items':[row]},self.config,self.now)
    def test_no_amazon_activation_or_tracking_in_canonical_target(self):
        config=copy.deepcopy(self.config);config['amazonUk']['enabled']=True
        with self.assertRaises(ValueError):validate_offers(self.data,config,self.now)
        for target in ['https://www.ebay.co.uk/itm/123456789012?campid=123','https://www.ebay.co.uk.evil.test/itm/123456789012','https://www.ebay.co.uk/itm/123456789012#offer']:
            with self.assertRaises(ValueError):ebay_link(target,self.config)

if __name__=='__main__':unittest.main()

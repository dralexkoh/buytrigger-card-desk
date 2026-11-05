import copy,json,unittest
from pathlib import Path
from validate_drops import validate_drops
ROOT=Path(__file__).resolve().parents[1]

class DropsContract(unittest.TestCase):
    def setUp(self): self.data=json.loads((ROOT/'drops.json').read_text())
    def test_reviewed_seed_and_regional_identity(self):
        self.assertTrue(validate_drops(self.data,ROOT))
        self.assertEqual({i['country'] for i in self.data['items']},{'United Kingdom','United States','Japan','Hong Kong','Singapore','Philippines','Taiwan'})
        self.assertEqual(len(self.data['items']),9)
    def test_duplicate_region_and_vague_asia_rejected(self):
        self.data['items'].append(copy.deepcopy(self.data['items'][0]))
        with self.assertRaises(AssertionError): validate_drops(self.data,ROOT)
        self.setUp();self.data['items'][-1]['country']='Asia'
        with self.assertRaises(AssertionError): validate_drops(self.data,ROOT)
    def test_release_cannot_silently_become_stock_offer(self):
        self.data['items'][0]['stock']='In stock'
        with self.assertRaises(AssertionError): validate_drops(self.data,ROOT)
        self.data['items'][0].update(stockSourceUrl='https://example.com/product',stockCheckedAt='2026-01-01T00:00:00Z',stockExpiresAt='2026-01-01T01:00:00Z')
        with self.assertRaises(AssertionError): validate_drops(self.data,ROOT)
    def test_bad_date_and_missing_source_rejected(self):
        self.data['items'][0]['date']='2026-11-31'
        with self.assertRaises(ValueError): validate_drops(self.data,ROOT)
        self.setUp();self.data['items'][0]['sourceUrl']=None
        with self.assertRaises(AssertionError): validate_drops(self.data,ROOT)

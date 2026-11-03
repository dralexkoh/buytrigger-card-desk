import copy,tempfile,unittest
from pathlib import Path
from editorial_visuals import validate_editorial_visuals

class EditorialVisualTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'assets').mkdir();(self.root/'assets/cover.svg').write_text('<svg/>')
        self.data={'articles':[{'slug':'example','image':'assets/cover.svg','imageAlt':'A collecting illustration','imageCredit':'Original editorial illustration','visualStyle':'brand-graphic-v1'}]}
    def tearDown(self):self.temp.cleanup()
    def test_deliberate_art_passes(self):self.assertEqual(validate_editorial_visuals(self.data,self.root),1)
    def test_missing_credit_or_unknown_style_blocks_publication(self):
        for field,value in [('imageCredit',''),('visualStyle','new-random-style')]:
            with self.subTest(field=field):
                d=copy.deepcopy(self.data);d['articles'][0][field]=value
                with self.assertRaises(ValueError):validate_editorial_visuals(d,self.root)
    def test_absent_image_or_path_escape_never_falls_back(self):
        (self.root/'outside.svg').write_text('<svg/>')
        for value in ['assets/missing.svg','assets/../outside.svg','https://example.com/image.jpg']:
            with self.subTest(path=value):
                d=copy.deepcopy(self.data);d['articles'][0]['image']=value
                with self.assertRaises(ValueError):validate_editorial_visuals(d,self.root)
    def test_press_asset_cannot_be_labelled_house_art(self):
        self.data['articles'][0]['pressAsset']=True
        with self.assertRaises(ValueError):validate_editorial_visuals(self.data,self.root)
        self.data['articles'][0]['visualStyle']='source-media-v1'
        self.assertEqual(validate_editorial_visuals(self.data,self.root),1)

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
    def quick_read(self):
        a=self.data['articles'][0];a['editorialFormat']='visual-quick-read-v1'
        a['sections']=[{'heading':'The story','html':'<aside class="quick-verdict">Key takeaway</aside><figure class="feature-reference"><img src="assets/cover.svg" alt="Official box reference"><figcaption>Product reference, publisher credited.</figcaption></figure><div class="closing-call">Clear conclusion</div>'}]
        return a
    def test_visual_quick_read_complete_package_passes(self):
        self.quick_read();self.assertEqual(validate_editorial_visuals(self.data,self.root),1)
    def test_visual_quick_read_missing_verdict_is_rejected(self):
        a=self.quick_read();a['sections'][0]['html']=a['sections'][0]['html'].replace('closing-call','other')
        with self.assertRaises(ValueError):validate_editorial_visuals(self.data,self.root)
    def test_inline_broken_asset_and_missing_alt_are_rejected(self):
        a=self.quick_read();original=a['sections'][0]['html']
        for old,new in [('assets/cover.svg','assets/missing.svg'),('alt="Official box reference"','alt=""')]:
            with self.subTest(change=old):
                a['sections'][0]['html']=original.replace(old,new)
                with self.assertRaises(ValueError):validate_editorial_visuals(self.data,self.root)
    def test_inline_source_caption_cannot_disappear(self):
        a=self.quick_read();a['sections'][0]['html']=a['sections'][0]['html'].replace('<figcaption>Product reference, publisher credited.</figcaption>','')
        with self.assertRaises(ValueError):validate_editorial_visuals(self.data,self.root)

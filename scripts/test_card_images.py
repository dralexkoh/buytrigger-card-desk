"""Local pictures for Feature and news Buy on eBay blocks. No network."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from card_images import block_cards, card_images, image_for

ROOT = Path(__file__).resolve().parents[1]
UMBREON = 'Umbreon ex|161/131|Prismatic Evolutions'
MISSING = {
    'Moltres|30/110|Legendary Collection',
    'Umbreon (Poke Ball Pattern)|059/131|Prismatic Evolutions',
    'Espeon (Master Ball Pattern)|033/131|Prismatic Evolutions',
}


class CardImages(unittest.TestCase):
    def setUp(self):
        self.cards = block_cards(ROOT)
        self.images = card_images(ROOT)

    def test_blocks_match_shipped_files_and_leave_three_without_a_picture(self):
        self.assertEqual(len(self.cards), 52)
        self.assertEqual(len(self.images), 49)
        keys = {f"{card['name']}|{card['number']}|{card['set']}" for card in self.cards}
        self.assertEqual(set(self.images) | MISSING, keys)
        for key in MISSING:
            self.assertNotIn(key, self.images)
            name, number, set_name = key.split('|')
            self.assertIsNone(image_for(ROOT, name, number, set_name))

    def test_set_tracker_jpg_beats_the_modern_index_and_the_set_must_match(self):
        self.assertEqual(self.images[UMBREON], 'assets/prismatic-evolutions/610516.jpg')
        self.assertEqual(self.images['Charizard ex|199/165|Scarlet & Violet 151'], 'assets/sv-151/517045.jpg')
        self.assertEqual(self.images['Mega Rayquaza ex|138/103|Delta Reign'], 'assets/delta-reign/728061.jpg')
        self.assertEqual(self.images['Charizard|4/102|30th Celebration'], 'assets/thirtieth/714372.jpg')
        self.assertEqual(self.images['Lugia|149/147|30th Celebration'], 'assets/thirtieth/714386.jpg')
        self.assertIsNone(image_for(ROOT, 'Charizard', '4/102', 'Base Set'))
        self.assertIsNone(image_for(ROOT, 'Umbreon ex', '161/131', 'Evolving Skies'))

    def test_modern_index_webp_is_the_fallback_when_no_set_file_exists(self):
        self.assertEqual(self.images['Umbreon VMAX|215/203|Evolving Skies'], 'assets/modern-006-low.webp')
        self.assertEqual(self.images['Rayquaza VMAX|218/203|Evolving Skies'], 'assets/modern-010-low.webp')
        self.assertEqual(self.images['Lugia V|186/195|Silver Tempest'], 'assets/modern-049-low.webp')
        self.assertEqual(self.images['Pikachu ex|238/191|Surging Sparks'], 'assets/modern-092-low.webp')

    def test_a_pattern_card_uses_the_one_shipped_file_named_with_its_product(self):
        path = self.images['Umbreon (Master Ball Pattern)|059/131|Prismatic Evolutions']
        self.assertEqual(path, 'assets/newsroom-20261119c/prismatic-master-ball-umbreon-610679.webp')
        self.assertNotEqual(path, self.images[UMBREON])

    def test_every_path_is_a_local_asset_and_the_module_does_not_fetch(self):
        source = (ROOT / 'scripts' / 'card_images.py').read_text()
        for banned in ('urllib', 'requests', 'httpx', 'socket', 'urlopen', 'tcgplayer-cdn', 'cloudflare'):
            self.assertNotIn(banned, source)
        for key, path in self.images.items():
            self.assertTrue(path.startswith('assets/'), key)
            self.assertNotIn('..', path)
            self.assertFalse(path.startswith('http'), key)
            self.assertTrue((ROOT / path).is_file(), path)


if __name__ == '__main__':
    unittest.main()

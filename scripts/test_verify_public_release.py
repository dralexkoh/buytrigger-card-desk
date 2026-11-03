"""Verify content and final HTTPS origin without external network requests."""
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from urllib.parse import urlsplit

import verify_public_release as V


class Response:
    def __init__(self, content, url):
        self.content, self.url = content, url

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def read(self):
        return self.content

    def geturl(self):
        return self.url


class LiveVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dist = Path(self.temp.name)
        for name in V.NAMES:
            target = self.dist/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('verified artifact: '+name)

    def response(self, request, origin=V.PRIMARY_URL, stale=False):
        path = urlsplit(request.full_url).path.removeprefix('/buytrigger-card-desk/').lstrip('/')
        content = b'previous artifact' if stale else (self.dist/path).read_bytes()
        return Response(content, origin+path)

    def test_legacy_input_must_redirect_to_matching_primary_site(self):
        with mock.patch.object(V.urllib.request, 'urlopen', side_effect=lambda request, **_: self.response(request)) as fetch:
            self.assertEqual(V.verify(self.dist, 'https://dralexkoh.github.io/buytrigger-card-desk/', attempts=1), {})
        self.assertEqual(fetch.call_count, len(V.NAMES))

    def test_matching_content_on_an_old_or_insecure_host_is_not_cutover(self):
        for origin in ['https://dralexkoh.github.io/buytrigger-card-desk/', 'http://buytrigger.cards/', 'https://www.buytrigger.cards/']:
            with mock.patch.object(V.urllib.request, 'urlopen', side_effect=lambda request, **_: self.response(request, origin)):
                self.assertEqual(set(V.verify(self.dist, attempts=1)), set(V.NAMES))

    def test_cdn_retry_fetches_only_remaining_mismatch(self):
        calls = []
        def fetch(request, **_):
            calls.append(request.full_url)
            return self.response(request, stale=len(calls)==1)
        with mock.patch.object(V.urllib.request, 'urlopen', side_effect=fetch), mock.patch.object(V.time, 'sleep') as sleep:
            self.assertEqual(V.verify(self.dist, attempts=2), {})
        self.assertEqual(len(calls), len(V.NAMES)+1)
        self.assertEqual(calls[0], calls[-1])
        sleep.assert_called_once_with(10)


if __name__=='__main__':
    unittest.main()

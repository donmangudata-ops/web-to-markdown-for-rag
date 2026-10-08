import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import web_to_markdown as w  # noqa: E402

ARTICLE = """<html><head><title>How sitemaps work</title><meta name="date" content="2026-09-01"></head><body>
<nav><a href="/">Home</a> | <a href="/pricing">Pricing</a> | <a href="/login">Log in</a></nav>
<article><h1>How sitemaps work</h1>
<p>A sitemap is a file that lists the pages of a website. Search engines read it to find pages they might miss when they follow links.</p>
<h2>Sitemap index files</h2>
<p>Large sites split their sitemap into many files. A sitemap index lists those files, and each one lists up to fifty thousand URLs.</p>
<p>Many sites also compress their sitemaps with gzip to save bandwidth, and some publish a plain text list instead of XML.</p>
<table><tr><th>Format</th><th>Extension</th></tr><tr><td>XML</td><td>.xml</td></tr><tr><td>Text</td><td>.txt</td></tr></table>
</article>
<footer>Copyright 2026. Cookie settings. Contact us.</footer></body></html>"""

PAGES = {"https://a.test/sitemaps": ARTICLE, "https://a.test/copy": ARTICLE, "https://a.test/empty": "<html><body></body></html>"}


def fake_fetch(url, ua, timeout=30):
    if url not in PAGES:
        raise OSError("HTTP Error 404")
    return PAGES[url]


class MarkdownTest(unittest.TestCase):
    def test_run(self):
        out = tempfile.mkdtemp()
        n = w.run(list(PAGES) + ["https://a.test/missing"], out, delay=0, fetcher=fake_fetch)
        self.assertEqual(n, 1)
        rows = [json.loads(l) for l in open(os.path.join(out, "manifest.jsonl"))]
        status = {r["source"]: r["status"] for r in rows}
        self.assertEqual(status["https://a.test/copy"], "skipped: duplicate content")
        self.assertTrue(status["https://a.test/empty"].startswith("skipped"))
        self.assertTrue(status["https://a.test/missing"].startswith("failed"))
        saved = next(r for r in rows if r["status"] == "saved")
        text = open(os.path.join(out, saved["file"]), encoding="utf-8").read()
        self.assertIn('source: "https://a.test/sitemaps"', text)
        self.assertIn("Sitemap index files", text)
        self.assertNotIn("Cookie settings", text)
        self.assertNotIn("Log in", text)

    def test_chunks(self):
        parts = w.chunk("a" * 50 + "\n\n" + "b" * 50 + "\n\n" + "c" * 50, 110)
        self.assertEqual([len(p) for p in parts], [102, 50])

    def test_slug_is_stable_and_safe(self):
        s = w.slug("https://Example.com/a b?x=1")
        self.assertEqual(s, w.slug("https://Example.com/a b?x=1"))
        self.assertRegex(s, r"^[a-z0-9-]+$")


if __name__ == "__main__":
    unittest.main()

"""web-to-markdown-for-rag: turn a list of URLs into clean Markdown files for a RAG index.

The main text of each page is extracted with trafilatura (menus, footers and ads removed).
Each file gets YAML front matter with the source URL, title, date and a content hash,
and the run writes manifest.jsonl, which most RAG loaders can read.

Usage:
    python web_to_markdown.py urls.txt -o docs
    python web_to_markdown.py urls.txt -o docs --chunk-chars 2000
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import trafilatura

DEFAULT_UA = "web-to-markdown-for-rag/1.0 (+https://github.com/donmangudata-ops/web-to-markdown-for-rag)"


def slug(url):
    s = re.sub(r"^https?://", "", url).strip("/")
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return (s[:80] or "page") + "-" + hashlib.sha1(url.encode()).hexdigest()[:8]


def chunk(text, size):
    """Split on paragraph boundaries into chunks of at most `size` characters (a long paragraph stays whole)."""
    if not size:
        return [text]
    out, cur = [], ""
    for para in text.split("\n\n"):
        if cur and len(cur) + len(para) + 2 > size:
            out.append(cur)
            cur = para
        else:
            cur = f"{cur}\n\n{para}" if cur else para
    if cur:
        out.append(cur)
    return out


def convert(url, html):
    """Return (markdown, metadata) or (None, reason)."""
    md = trafilatura.extract(html, url=url, output_format="markdown", include_links=True,
                             include_tables=True, include_comments=False, favor_precision=True)
    if not md or not md.strip():
        return None, "no main text found"
    meta = trafilatura.extract_metadata(html, default_url=url)
    return md.strip(), {
        "source": url,
        "title": (meta.title if meta and meta.title else "").strip(),
        "date": (meta.date if meta and meta.date else ""),
        "fetched": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sha256": hashlib.sha256(md.encode()).hexdigest(),
    }


def front_matter(meta):
    lines = ["---"] + [f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in meta.items()] + ["---", ""]
    return "\n".join(lines)


def fetch(url, user_agent, timeout=30):
    from urllib.request import Request, urlopen
    with urlopen(Request(url, headers={"User-Agent": user_agent}), timeout=timeout) as r:
        raw = r.read()
        charset = r.headers.get_content_charset() or "utf-8"
    return raw.decode(charset, "replace")


def run(urls, out_dir, chunk_chars=0, user_agent=DEFAULT_UA, delay=0.5, fetcher=fetch):
    os.makedirs(out_dir, exist_ok=True)
    done, seen = 0, set()
    with open(os.path.join(out_dir, "manifest.jsonl"), "w", encoding="utf-8") as manifest:
        for url in urls:
            time.sleep(delay)
            try:
                md, meta = convert(url, fetcher(url, user_agent))
            except Exception as e:  # network or parse error: log and go on
                manifest.write(json.dumps({"source": url, "status": f"failed: {e}"}) + "\n")
                continue
            if md is None:
                manifest.write(json.dumps({"source": url, "status": f"skipped: {meta}"}) + "\n")
                continue
            if meta["sha256"] in seen:
                manifest.write(json.dumps({"source": url, "status": "skipped: duplicate content"}) + "\n")
                continue
            seen.add(meta["sha256"])
            parts = chunk(md, chunk_chars)
            for i, part in enumerate(parts, 1):
                name = slug(url) + (f"-{i:03d}" if len(parts) > 1 else "") + ".md"
                m = dict(meta, chunk=i, chunks=len(parts)) if len(parts) > 1 else meta
                with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
                    f.write(front_matter(m) + part + "\n")
                manifest.write(json.dumps(dict(m, file=name, status="saved", chars=len(part)), ensure_ascii=False) + "\n")
            done += 1
    return done


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", help="text file: one URL per line")
    p.add_argument("-o", "--out", default="docs")
    p.add_argument("--chunk-chars", type=int, default=0, help="split pages into chunks of about this many characters (0 = one file per page)")
    p.add_argument("--user-agent", default=DEFAULT_UA)
    p.add_argument("--delay", type=float, default=0.5, help="seconds between requests")
    a = p.parse_args(argv)
    with open(a.input, encoding="utf-8") as f:
        urls = list(dict.fromkeys(l.strip() for l in f if l.strip() and not l.startswith("#")))
    n = run(urls, a.out, a.chunk_chars, a.user_agent, a.delay)
    print(f"{n} of {len(urls)} pages converted; see {a.out}/manifest.jsonl", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

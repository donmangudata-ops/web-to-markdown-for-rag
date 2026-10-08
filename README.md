# web-to-markdown-for-rag

Turn a list of URLs into clean Markdown files, ready to load into a RAG index or give to an LLM. One Python file. Main-text extraction by [trafilatura](https://github.com/adbar/trafilatura).

What you get for each page:

- The main text as Markdown, with headings, lists, tables and links. Menus, footers, cookie banners and comments are removed.
- YAML front matter: `source`, `title`, `date`, `fetched`, `sha256`.
- Optional chunks on paragraph boundaries (`--chunk-chars`), each with `chunk` and `chunks` fields.

And for the whole run, `manifest.jsonl` with one line per page or chunk: saved, skipped (no main text, duplicate content) or failed, with the reason. Pages with the same text are saved once.

## Install

```bash
git clone https://github.com/donmangudata-ops/web-to-markdown-for-rag
cd web-to-markdown-for-rag
pip install -r requirements.txt
```

## Usage

One URL per line in a text file, then:

```bash
python web_to_markdown.py urls.txt -o docs
python web_to_markdown.py urls.txt -o docs --chunk-chars 2000
```

Example output file `docs/example-com-blog-sitemaps-1a2b3c4d.md`:

```markdown
---
source: "https://example.com/blog/sitemaps"
title: "How sitemaps work"
date: "2026-09-01"
fetched: "2026-10-08T10:00:00Z"
sha256: "..."
---
# How sitemaps work

A sitemap is a file that lists the pages of a website...
```

Need the list of URLs first? [sitemap-url-inventory](https://github.com/donmangudata-ops/sitemap-url-inventory) exports every URL from a site's sitemaps.

## Load into a RAG pipeline

Each file is plain Markdown with front matter, so most loaders work directly. For example, read `manifest.jsonl`, keep the rows with `"status": "saved"`, and load each `file` with its `source` and `title` as metadata.

## Limits

- The script fetches plain HTML. Pages that need JavaScript to show their text come back as "no main text found".
- It waits 0.5 seconds between requests (`--delay`). Set `--user-agent` to something that identifies you, and respect sites that block automated access.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Hosted version (optional)

If you don't want to run this yourself, I also sell a hosted version on Apify: [Web Page to Markdown](https://apify.com/conserving_celerytop/web-page-to-markdown?utm_source=github&utm_medium=readme&utm_campaign=web-to-markdown-for-rag). It runs in the cloud and connects to Make, n8n, Zapier and AI agents.

Disclosure: I built that Actor, and it is paid. This repository is free and works without it. The code was written with help from an AI assistant and is covered by the tests above.

## License

MIT. trafilatura is licensed under Apache-2.0.

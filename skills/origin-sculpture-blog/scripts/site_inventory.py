#!/usr/bin/env python3
"""Crawl a Shopify sitemap and rank canonical internal-link candidates."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

USER_AGENT = "OriginSculptureBlogSkill/2.4.0 (+https://originsculpture.com)"
MAX_SITEMAPS = 50
MAX_URLS = 10000

SYNONYMS = {
    "finish": {"surface", "polish", "polished", "matte", "brushed", "texture", "patina", "color", "sample"},
    "metal": {"stainless", "steel", "bronze", "copper"},
    "stone": {"marble", "limestone", "granite", "carved"},
    "fiberglass": {"frp", "resin", "gelcoat", "color"},
    "outdoor": {"garden", "landscape", "exterior", "public"},
    "indoor": {"interior", "lobby", "hotel", "residence"},
    "care": {"maintenance", "cleaning", "preservation"},
    "custom": {"bespoke", "commission", "sample"},
}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/xml,text/xml,*/*"})
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}: {url}")
        return response.read(20_000_000)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def first_descendant_text(node: ET.Element, wanted: str) -> str:
    for child in node.iter():
        if local_name(child.tag) == wanted and child.text:
            return child.text.strip()
    return ""


def kind_for(url: str) -> str:
    path = urllib.parse.urlparse(url).path
    if "/products/" in path:
        return "product"
    if "/collections/" in path:
        return "collection"
    if "/blogs/" in path:
        return "article"
    if "/pages/" in path:
        return "page"
    return "other"


def normalize_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/") or "/", parsed.query, ""))


def crawl(site: str) -> dict:
    site_url = site if "://" in site else f"https://{site}"
    site_parsed = urllib.parse.urlparse(site_url)
    origin_host = site_parsed.netloc.lower().removeprefix("www.")
    queue = [urllib.parse.urljoin(site_url.rstrip("/") + "/", "sitemap.xml")]
    seen_maps: set[str] = set()
    items: dict[str, dict] = {}

    while queue:
        sitemap_url = queue.pop(0)
        if sitemap_url in seen_maps:
            continue
        if len(seen_maps) >= MAX_SITEMAPS:
            raise RuntimeError(f"Sitemap limit exceeded ({MAX_SITEMAPS})")
        seen_maps.add(sitemap_url)
        root = ET.fromstring(fetch(sitemap_url))
        root_name = local_name(root.tag)
        if root_name == "sitemapindex":
            for sitemap in root:
                loc = first_descendant_text(sitemap, "loc")
                if loc:
                    host = urllib.parse.urlparse(loc).netloc.lower().removeprefix("www.")
                    if host == origin_host:
                        queue.append(loc)
            continue
        if root_name != "urlset":
            continue
        for url_node in root:
            loc = first_descendant_text(url_node, "loc")
            if not loc:
                continue
            canonical = normalize_url(loc)
            host = urllib.parse.urlparse(canonical).netloc.lower().removeprefix("www.")
            if host != origin_host:
                continue
            items[canonical] = {
                "url": canonical,
                "kind": kind_for(canonical),
                "title": first_descendant_text(url_node, "title"),
                "caption": first_descendant_text(url_node, "caption"),
                "lastmod": first_descendant_text(url_node, "lastmod"),
            }
            if len(items) > MAX_URLS:
                raise RuntimeError(f"URL limit exceeded ({MAX_URLS})")

    return {
        "site": f"{site_parsed.scheme or 'https'}://{site_parsed.netloc}",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sitemaps": sorted(seen_maps),
        "count": len(items),
        "items": sorted(items.values(), key=lambda item: (item["kind"], item["url"])),
    }


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def expanded_query(query: str) -> set[str]:
    base = set(tokens(query))
    expanded = set(base)
    for term in list(base):
        expanded.update(SYNONYMS.get(term, set()))
        for key, values in SYNONYMS.items():
            if term in values:
                expanded.add(key)
                expanded.update(values)
    return expanded


def rank(inventory: dict, query: str, kind: str, limit: int) -> list[dict]:
    query_tokens = expanded_query(query)
    exact = query.lower().strip()
    candidates = [item for item in inventory.get("items", []) if kind == "all" or item.get("kind") == kind]
    document_frequency: dict[str, int] = {}
    docs = []
    for item in candidates:
        text = " ".join([item.get("title", ""), item.get("caption", ""), urllib.parse.unquote(item.get("url", ""))]).lower()
        doc_tokens = tokens(text)
        docs.append((item, text, doc_tokens))
        for token in set(doc_tokens):
            document_frequency[token] = document_frequency.get(token, 0) + 1
    total = max(len(docs), 1)
    ranked = []
    for item, text, doc_tokens in docs:
        counts = {token: doc_tokens.count(token) for token in set(doc_tokens)}
        score = 8.0 if exact and exact in text else 0.0
        matched = []
        for token in query_tokens:
            if token in counts:
                idf = math.log((total + 1) / (document_frequency.get(token, 0) + 1)) + 1
                score += (1 + math.log(counts[token])) * idf
                matched.append(token)
        if score > 0:
            enriched = dict(item)
            enriched["score"] = round(score, 3)
            enriched["matchedTerms"] = sorted(matched)
            ranked.append(enriched)
    ranked.sort(key=lambda item: (-item["score"], item.get("title", ""), item["url"]))
    return ranked[:limit]


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    crawl_parser = sub.add_parser("crawl", help="crawl the site's sitemap")
    crawl_parser.add_argument("--site", required=True)
    crawl_parser.add_argument("--output", required=True, type=Path)
    search_parser = sub.add_parser("search", help="rank URLs from a saved inventory")
    search_parser.add_argument("--inventory", required=True, type=Path)
    search_parser.add_argument("--query", required=True)
    search_parser.add_argument("--kind", choices=["all", "product", "collection", "article", "page", "other"], default="all")
    search_parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    try:
        if args.command == "crawl":
            result = crawl(args.site)
            write_json(args.output, result)
            counts: dict[str, int] = {}
            for item in result["items"]:
                counts[item["kind"]] = counts.get(item["kind"], 0) + 1
            print(json.dumps({"output": str(args.output), "count": result["count"], "kinds": counts}, ensure_ascii=False))
        else:
            inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
            print(json.dumps(rank(inventory, args.query, args.kind, args.limit), indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

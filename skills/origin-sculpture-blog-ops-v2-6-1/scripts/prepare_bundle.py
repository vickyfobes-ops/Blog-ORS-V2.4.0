#!/usr/bin/env python3
"""Audit an Origin blog bundle and create a hash-bound Shopify payload."""

from __future__ import annotations

import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_SOURCE_FILES = [
    "meta.json", "article.md", "article.html", "summary.html", "sources.md", "link-plan.json",
    "image-assets.json",
]
IMAGE_MANIFEST = "image-assets.json"
UPDATE_TARGET_MANIFEST = "update-target.json"
CONTENT_TIER_RANGES = {
    "pillar": (1800, 2500),
    "supporting": (1000, 1600),
}
EDITORIAL_MODES = {"site-led", "expert-led"}
IMAGE_SOURCE_TYPES = {"generated-editorial", "origin-owned", "user-provided"}
IMAGE_VISUAL_ROLES = {"environment-scene", "process-scene", "material-detail", "product-evidence"}
IMAGE_VISUAL_QA_KEYS = (
    "inspected",
    "noScreenUiTextLogo",
    "realisticMaterialScale",
    "sectionRelevant",
)
NORMALIZED_IMAGE_SIZE = (1600, 900)
ORIGIN_IMAGE_SOURCE_HOSTS = {"originsculpture.com", "www.originsculpture.com", "cdn.shopify.com"}
EXPERIENCE_START = "<!-- origin-experience:start -->"
EXPERIENCE_END = "<!-- origin-experience:end -->"
EXPERIENCE_SIGNAL_GROUPS = {
    "materialSelection": (
        "material selection", "material choice", "substrate", "alloy", "stone species", "fiberglass system",
    ),
    "finishApproval": (
        "finish approval", "approved finish", "physical sample", "control sample", "signed sample",
        "sample approval", "finish schedule",
    ),
    "productionProcess": (
        "production", "fabrication", "casting", "welding", "polishing", "surface preparation",
    ),
    "qualityControl": (
        "quality control", "inspection", "mockup", "tolerance", "qc checkpoint", "qc review",
    ),
    "installationEnvironment": (
        "installation environment", "site condition", "installation", "anchoring", "drainage", "lifting",
        "packing", "transport",
    ),
    "maintenanceInspection": (
        "maintenance", "cleaning", "inspection interval", "renewal", "repair", "care plan",
    ),
}
BLOG_FILTER_NAMESPACE = "custom"
BLOG_FILTER_KEY = "blog_filter"
BLOG_FILTER_CHOICES = (
    "Project Inspiration",
    "Sculpture Buying Guide",
    "Sculpture Materials Knowledge Center",
    "Sculpture Design Inspiration",
    "Sculpture Manufacturing & Craftsmanship",
    "Sculpture Trends",
    "Sculpture Maintenance Guide",
)
BLOG_FILTER_SIGNALS = {
    "Sculpture Maintenance Guide": (
        "maintenance", "care", "cleaning", "clean", "restore", "restoration", "repair", "corrosion prevention",
    ),
    "Sculpture Trends": (
        "trend", "trends", "forecast", "emerging", "what's next", "what is next", "2026", "2027", "2028",
    ),
    "Sculpture Materials Knowledge Center": (
        "material", "materials", "stainless steel", "bronze", "stone", "marble", "granite", "fiberglass",
        "finish", "finishes", "surface", "patina", "polished", "brushed", "coating", "alloy",
    ),
    "Sculpture Manufacturing & Craftsmanship": (
        "manufacturing", "craftsmanship", "fabrication", "fabricated", "welding", "casting", "foundry",
        "production", "quality control", "workshop", "mold", "mould",
    ),
    "Sculpture Buying Guide": (
        "buying", "buy", "ordering", "order", "cost", "price", "budget", "choose", "choosing", "selection",
        "procurement", "commission", "custom sculpture", "delivery", "site preparation", "placement", "scale",
    ),
    "Sculpture Design Inspiration": (
        "design inspiration", "style", "abstract", "figurative", "concept", "color", "form", "shape",
        "composition", "design ideas",
    ),
    "Project Inspiration": (
        "project inspiration", "case study", "installed project", "hotel lobby", "garden", "landscape project",
        "public art project", "residential project", "commercial project", "project ideas",
    ),
}
TITLE_FILTER_RULES = (
    ("Sculpture Maintenance Guide", ("maintenance", "care guide", "cleaning", "restoration")),
    ("Sculpture Trends", ("trend", "trends", "forecast", "what's next", "what is next")),
    ("Sculpture Manufacturing & Craftsmanship", ("manufacturing", "craftsmanship", "fabrication", "casting", "welding")),
    ("Project Inspiration", ("project inspiration", "case study", "installed project")),
    ("Sculpture Design Inspiration", ("design inspiration", "design ideas")),
    ("Sculpture Buying Guide", ("buying", "buy ", "ordering", "order ", "cost", "price", "budget", "site preparation", "placement", "scale guide")),
    ("Sculpture Materials Knowledge Center", ("material", "finish", "surface", "stainless steel", "bronze", "stone", "fiberglass")),
)
FORBIDDEN_TAGS = {"script", "iframe", "form", "object", "embed", "html", "head", "body"}
PLACEHOLDER_PATTERNS = [
    r"\[BUSINESS INPUT NEEDED:",
    r"\bTBD\b",
    r"\bTODO\b",
    r"example\.com",
    r"localhost",
    r"shopifypreview\.com",
    r"preview_theme_id=",
]
USER_AGENT = "OriginSculptureBlogSkill/2.6.1 (+https://originsculpture.com)"


def validate_content_tier(meta: dict) -> tuple[str, tuple[int, int]]:
    tier = str(meta.get("contentTier", "")).strip().lower()
    if tier not in CONTENT_TIER_RANGES:
        raise ValueError("contentTier must be either 'pillar' or 'supporting'")
    return tier, CONTENT_TIER_RANGES[tier]


def validate_editorial_mode(meta: dict) -> str:
    mode = str(meta.get("editorialMode", "")).strip().lower()
    if mode not in EDITORIAL_MODES:
        raise ValueError("editorialMode must be either 'site-led' or 'expert-led'")
    return mode


def origin_experience_evidence(sources: str) -> list[str]:
    marker = re.search(r"^## Origin experience evidence\s*$", sources, re.I | re.M)
    if not marker:
        return []
    remainder = sources[marker.end():]
    next_heading = re.search(r"^##\s+", remainder, re.M)
    section = remainder[: next_heading.start()] if next_heading else remainder
    evidence = []
    for line in section.splitlines():
        cleaned = line.strip()
        if not cleaned.startswith("-"):
            continue
        if "originsculpture.com" in cleaned.lower() or "[user-provided evidence" in cleaned.lower():
            evidence.append(cleaned)
    return evidence


def audit_origin_experience(body: str, total_words: int) -> dict:
    start_count = body.count(EXPERIENCE_START)
    end_count = body.count(EXPERIENCE_END)
    if start_count != 1 or end_count != 1:
        raise ValueError("article.html must contain exactly one matched Origin experience marker pair")
    start = body.index(EXPERIENCE_START) + len(EXPERIENCE_START)
    end = body.index(EXPERIENCE_END)
    if end <= start:
        raise ValueError("Origin experience markers are out of order")
    fragment = body[start:end]
    parsed = ArticleParser()
    parsed.feed(fragment)
    parsed.close()
    fragment_text = " ".join(parsed.text_parts)
    experience_words = len(words(fragment_text))
    ratio = experience_words / total_words if total_words else 0.0
    headings = [text for tag, text in parsed.headings if tag in {"h2", "h3"}]
    if not headings:
        raise ValueError("Origin experience section needs a topic-specific H2 or H3")
    if any(re.fullmatch(r"why choose origin(?: sculpture)?\??", heading.strip(), re.I) for heading in headings):
        raise ValueError("Use a topic-specific experience heading instead of 'Why Choose Origin'")
    if not re.search(r"\bOrigin Sculpture\b", fragment_text):
        raise ValueError("Origin experience section must clearly attribute the practice to Origin Sculpture")
    lowered = f" {fragment_text.lower()} "
    signals = sorted(
        name for name, terms in EXPERIENCE_SIGNAL_GROUPS.items() if any(term in lowered for term in terms)
    )
    if len(signals) < 2:
        raise ValueError("Origin experience section must connect at least two topic-relevant experience signals")
    return {
        "words": experience_words,
        "ratio": ratio,
        "headings": headings,
        "signals": signals,
    }


def classify_blog_filters(meta: dict, body_text: str) -> tuple[list[str], str]:
    """Return one conservative primary filter and whether it was explicit or inferred."""
    explicit = meta.get("blogFilters")
    if explicit is not None:
        if not isinstance(explicit, list):
            raise ValueError("blogFilters must be a JSON array")
        filters = [str(value).strip() for value in explicit if str(value).strip()]
        if len(filters) != len(set(filters)):
            raise ValueError("blogFilters must not contain duplicates")
        if not filters:
            raise ValueError("blogFilters must contain at least one value")
        if len(filters) > 2:
            raise ValueError("blogFilters may contain at most two focused values")
        unknown = [value for value in filters if value not in BLOG_FILTER_CHOICES]
        if unknown:
            raise ValueError(f"unsupported Blog Filter value(s): {', '.join(unknown)}")
        return filters, "explicit"

    title = str(meta.get("title", "")).lower()
    tags = " ".join(str(tag) for tag in meta.get("tags", []) if tag).lower()
    body = body_text.lower()[:12000]
    for category, signals in TITLE_FILTER_RULES:
        if any(signal in title for signal in signals):
            return [category], "inferred"
    scores: dict[str, int] = {}
    for category, signals in BLOG_FILTER_SIGNALS.items():
        score = 0
        for signal in signals:
            score += title.count(signal) * 8
            score += tags.count(signal) * 4
            score += min(body.count(signal), 4)
        scores[category] = score
    best = max(BLOG_FILTER_CHOICES, key=lambda item: (scores.get(item, 0), -BLOG_FILTER_CHOICES.index(item)))
    if scores.get(best, 0) == 0:
        best = "Sculpture Buying Guide"
    return [best], "inferred"


def normalize_host(value: str) -> str:
    parsed = urllib.parse.urlparse(value if "://" in value else f"https://{value}")
    return parsed.netloc.lower().split(":", 1)[0].removeprefix("www.")


def canonical_url(url: str, site_domain: str) -> str:
    absolute = urllib.parse.urljoin(f"https://{site_domain}/", url)
    parsed = urllib.parse.urlsplit(absolute)
    return urllib.parse.urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/") or "/", parsed.query, ""))


class ArticleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[tuple[str, str]] = []
        self.links: list[dict[str, str]] = []
        self.images: list[dict[str, str]] = []
        self.tags: list[str] = []
        self.dangerous: list[str] = []
        self.text_parts: list[str] = []
        self.intro_parts: list[str] = []
        self._heading_tag = ""
        self._heading_text: list[str] = []
        self._anchor: dict[str, str] | None = None
        self._anchor_text: list[str] = []
        self._seen_h2 = False
        self._current_h2 = "(opening)"

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs_dict = {key.lower(): value or "" for key, value in attrs}
        self.tags.append(tag)
        if tag in FORBIDDEN_TAGS:
            self.dangerous.append(f"forbidden tag <{tag}>")
        for key, value in attrs_dict.items():
            if key.startswith("on"):
                self.dangerous.append(f"event handler attribute {key}")
            if key in {"href", "src"} and value.strip().lower().startswith(("javascript:", "data:text/html")):
                self.dangerous.append(f"unsafe {key} URL")
        if tag in {"h1", "h2", "h3", "h4"}:
            self._heading_tag = tag
            self._heading_text = []
            if tag == "h2":
                self._seen_h2 = True
        if tag == "a":
            self._anchor = attrs_dict
            self._anchor_text = []
        if tag == "img":
            self.images.append({"src": attrs_dict.get("src", ""), "alt": attrs_dict.get("alt", "")})

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == self._heading_tag:
            text = re.sub(r"\s+", " ", " ".join(self._heading_text)).strip()
            self.headings.append((tag, text))
            if tag == "h2":
                self._current_h2 = text
            self._heading_tag = ""
            self._heading_text = []
        if tag == "a" and self._anchor is not None:
            text = re.sub(r"\s+", " ", " ".join(self._anchor_text)).strip()
            self.links.append(
                {"href": self._anchor.get("href", ""), "text": text, "section": self._current_h2}
            )
            self._anchor = None
            self._anchor_text = []

    def handle_data(self, data: str) -> None:
        cleaned = re.sub(r"\s+", " ", data).strip()
        if not cleaned:
            return
        self.text_parts.append(cleaned)
        if not self._seen_h2:
            self.intro_parts.append(cleaned)
        if self._heading_tag:
            self._heading_text.append(cleaned)
        if self._anchor is not None:
            self._anchor_text.append(cleaned)


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'’.-]*", text)


def comparison_words(text: str) -> list[str]:
    return [token.lower().strip(".-") for token in words(text) if token.strip(".-")]


def markdown_article_words(review: str) -> list[str]:
    marker = re.search(r"^## Article\s*$", review, re.M)
    if not marker:
        return []
    article = review[marker.end():]
    article = re.sub(r"^#\s+[^\n]+\n", "", article, count=1, flags=re.M)
    article = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", article)
    article = re.sub(r"^\s*\|?[\s:|-]+\|?\s*$", "", article, flags=re.M)
    article = re.sub(r"^\s*(?:[-*+]|\d+\.)\s+", "", article, flags=re.M)
    article = re.sub(r"[`*_>#|]", " ", article)
    return comparison_words(article)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_bundle_path(bundle: Path, relative: str) -> Path:
    candidate = (bundle / relative).resolve()
    if bundle != candidate and bundle not in candidate.parents:
        raise ValueError(f"asset path escapes the bundle: {relative}")
    return candidate


def atomic_json(path: Path, payload: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def validate_link(url: str) -> tuple[bool, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return 200 <= response.status < 400, f"HTTP {response.status}"
    except urllib.error.HTTPError as exc:
        if exc.code not in {403, 405}:
            return False, f"HTTP {exc.code}"
    except Exception as exc:
        return False, str(exc)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Range": "bytes=0-1024"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            response.read(1024)
            return 200 <= response.status < 400, f"HTTP {response.status}"
    except Exception as exc:
        return False, str(exc)


def validate_normalized_image(path: Path, expected_format: str, slot: str) -> str | None:
    try:
        from PIL import Image
    except ImportError:
        return "run prepare_bundle.py with the Codex document Python runtime; Pillow is required for image QA"
    try:
        with Image.open(path) as image:
            image.load()
            if image.format != expected_format:
                return f"image asset '{slot}' is not a real {expected_format} file: {path.name}"
            if image.size != NORMALIZED_IMAGE_SIZE:
                return (
                    f"image asset '{slot}' must be normalized to "
                    f"{NORMALIZED_IMAGE_SIZE[0]}x{NORMALIZED_IMAGE_SIZE[1]}; found {image.width}x{image.height}"
                )
    except Exception as exc:
        return f"image asset '{slot}' could not be decoded: {path.name}: {exc}"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--check-links", action="store_true")
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    blockers: list[str] = []
    warnings: list[str] = []

    missing = [name for name in BASE_SOURCE_FILES if not (bundle / name).is_file()]
    if missing:
        print(json.dumps({"status": "BLOCKED", "blockers": [f"Missing source files: {', '.join(missing)}"]}, indent=2))
        return 1

    try:
        meta = json.loads((bundle / "meta.json").read_text(encoding="utf-8"))
        link_plan = json.loads((bundle / "link-plan.json").read_text(encoding="utf-8"))
    except Exception as exc:
        print(json.dumps({"status": "BLOCKED", "blockers": [f"Invalid JSON: {exc}"]}, indent=2))
        return 1

    required_meta = [
        "siteDomain", "blogHandle", "title", "seoTitle", "metaDescription", "handle", "author", "tags",
        "editorialMode",
    ]
    for field in required_meta:
        if not meta.get(field):
            blockers.append(f"meta.json missing {field}")
    handle = str(meta.get("handle", ""))
    if handle and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", handle):
        blockers.append("handle must use lowercase letters, digits, and single hyphens")
    site_domain = normalize_host(str(meta.get("siteDomain", "")))
    if not site_domain:
        blockers.append("siteDomain is invalid")
    if not isinstance(meta.get("tags", []), list):
        blockers.append("tags must be a JSON array")

    publication_action = str(meta.get("publicationAction", "create")).strip().lower()
    if publication_action not in {"create", "update"}:
        blockers.append("publicationAction must be either 'create' or 'update'")
    update_target: dict = {}
    update_target_path = bundle / UPDATE_TARGET_MANIFEST
    if publication_action == "update":
        if not update_target_path.is_file():
            blockers.append("update publication requires update-target.json captured from the live Shopify article")
        else:
            try:
                update_target = json.loads(update_target_path.read_text(encoding="utf-8"))
                article_id = str(update_target.get("articleId", ""))
                remote_fingerprint = str(update_target.get("remoteFingerprint", ""))
                if not re.fullmatch(r"gid://shopify/Article/\d+", article_id):
                    blockers.append("update-target.json has an invalid Shopify articleId")
                if str(update_target.get("handle", "")) != handle:
                    blockers.append("update-target.json handle does not match meta.json")
                if str(update_target.get("blogHandle", "")) != str(meta.get("blogHandle", "")):
                    blockers.append("update-target.json blogHandle does not match meta.json")
                if not re.fullmatch(r"[a-f0-9]{64}", remote_fingerprint):
                    blockers.append("update-target.json has an invalid remoteFingerprint")
            except Exception as exc:
                blockers.append(f"could not read update-target.json: {exc}")

    content_tier = ""
    content_range = (0, 0)
    try:
        content_tier, content_range = validate_content_tier(meta)
    except ValueError as exc:
        blockers.append(str(exc))

    editorial_mode = ""
    try:
        editorial_mode = validate_editorial_mode(meta)
    except ValueError as exc:
        blockers.append(str(exc))

    template_suffix = meta.get("templateSuffix")
    if template_suffix is not None:
        template_suffix = str(template_suffix).strip()
        if template_suffix and not re.fullmatch(r"[a-z0-9]+(?:[-_][a-z0-9]+)*", template_suffix):
            blockers.append("templateSuffix must be null or a lowercase Shopify template suffix")

    body = (bundle / "article.html").read_text(encoding="utf-8")
    review = (bundle / "article.md").read_text(encoding="utf-8")
    summary = (bundle / "summary.html").read_text(encoding="utf-8").strip()
    sources = (bundle / "sources.md").read_text(encoding="utf-8")
    parsed = ArticleParser()
    parsed.feed(body)
    parsed.close()

    blog_filters: list[str] = []
    blog_filter_source = ""
    try:
        blog_filters, blog_filter_source = classify_blog_filters(meta, " ".join(parsed.text_parts))
    except ValueError as exc:
        blockers.append(str(exc))

    image_manifest_path = bundle / IMAGE_MANIFEST
    image_assets: list[dict] = []
    asset_by_slot: dict[str, dict] = {}
    asset_source_hashes: dict[str, str] = {}
    if image_manifest_path.is_file():
        try:
            raw_assets = json.loads(image_manifest_path.read_text(encoding="utf-8"))
            if not isinstance(raw_assets, list):
                raise ValueError("image-assets.json must contain a JSON array")
            image_assets = raw_assets
            for index, item in enumerate(image_assets):
                if not isinstance(item, dict):
                    blockers.append(f"image asset {index + 1} is not an object")
                    continue
                slot = str(item.get("slot", "")).strip()
                png_relative = str(item.get("png", "")).strip()
                relative = str(item.get("webp", "")).strip()
                alt = str(item.get("alt", "")).strip()
                placement = str(item.get("placement", "")).strip()
                source_type = str(item.get("sourceType", "")).strip().lower()
                visual_role = str(item.get("visualRole", "")).strip().lower()
                visual_qa = item.get("visualQa")
                source_page = str(item.get("sourcePage", "")).strip()
                source_image_url = str(item.get("sourceImageUrl", "")).strip()
                if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slot):
                    blockers.append(f"image asset {index + 1} has an invalid slot")
                    continue
                if slot in asset_by_slot:
                    blockers.append(f"duplicate image asset slot: {slot}")
                    continue
                if not relative:
                    blockers.append(f"image asset '{slot}' is missing webp")
                    continue
                try:
                    asset_path = safe_bundle_path(bundle, relative)
                except ValueError as exc:
                    blockers.append(str(exc))
                    continue
                if not asset_path.is_file():
                    blockers.append(f"image asset file is missing: {relative}")
                    continue
                if asset_path.suffix.lower() != ".webp":
                    blockers.append(f"publishable image asset must be WebP: {relative}")
                else:
                    format_error = validate_normalized_image(asset_path, "WEBP", slot)
                    if format_error:
                        blockers.append(format_error)
                if not png_relative:
                    blockers.append(f"image asset '{slot}' is missing png for the Word artifact")
                else:
                    try:
                        png_path = safe_bundle_path(bundle, png_relative)
                        if not png_path.is_file():
                            blockers.append(f"Word image asset file is missing: {png_relative}")
                        elif png_path.suffix.lower() != ".png":
                            blockers.append(f"Word image asset must be PNG: {png_relative}")
                        else:
                            format_error = validate_normalized_image(png_path, "PNG", slot)
                            if format_error:
                                blockers.append(format_error)
                            asset_source_hashes[f"asset:{png_relative}"] = file_hash(png_path)
                    except ValueError as exc:
                        blockers.append(str(exc))
                if not alt:
                    blockers.append(f"image asset '{slot}' is missing alt text")
                if source_type not in IMAGE_SOURCE_TYPES:
                    blockers.append(
                        f"image asset '{slot}' sourceType must be one of: {', '.join(sorted(IMAGE_SOURCE_TYPES))}"
                    )
                if visual_role not in IMAGE_VISUAL_ROLES:
                    blockers.append(
                        f"image asset '{slot}' visualRole must be one of: {', '.join(sorted(IMAGE_VISUAL_ROLES))}"
                    )
                if source_type == "origin-owned":
                    if visual_role != "product-evidence":
                        blockers.append(
                            f"Origin-owned image asset '{slot}' must use visualRole 'product-evidence'"
                        )
                    parsed_source_page = urllib.parse.urlsplit(source_page)
                    if (
                        parsed_source_page.scheme != "https"
                        or normalize_host(source_page) != site_domain
                        or not parsed_source_page.path.startswith(("/products/", "/blogs/", "/pages/"))
                    ):
                        blockers.append(
                            f"Origin-owned image asset '{slot}' needs a canonical HTTPS sourcePage on originsculpture.com"
                        )
                    else:
                        source_page = canonical_url(source_page, site_domain)
                    parsed_source_image = urllib.parse.urlsplit(source_image_url)
                    if (
                        parsed_source_image.scheme != "https"
                        or (parsed_source_image.hostname or "").lower() not in ORIGIN_IMAGE_SOURCE_HOSTS
                        or not re.search(r"\.(?:avif|jpe?g|png|webp)$", parsed_source_image.path, re.I)
                    ):
                        blockers.append(
                            f"Origin-owned image asset '{slot}' needs its HTTPS sourceImageUrl from the Origin/Shopify CDN"
                        )
                if not isinstance(visual_qa, dict):
                    blockers.append(f"image asset '{slot}' is missing visualQa review results")
                    visual_qa = {}
                missing_visual_checks = [key for key in IMAGE_VISUAL_QA_KEYS if visual_qa.get(key) is not True]
                if missing_visual_checks:
                    blockers.append(
                        f"image asset '{slot}' failed or omitted visualQa: {', '.join(missing_visual_checks)}"
                    )
                if not placement:
                    blockers.append(f"image asset '{slot}' is missing placement guidance")
                elif slot == "cover":
                    if placement != "Shopify article cover image":
                        blockers.append("cover image placement must be 'Shopify article cover image'")
                    if source_type != "generated-editorial":
                        warnings.append("cover image normally uses a generated-editorial environment scene")
                    if visual_role != "environment-scene":
                        blockers.append("cover image visualRole must be 'environment-scene'")
                else:
                    placement_match = re.fullmatch(r"(?:Before|After)\s+(.+)", placement)
                    heading_texts = {text for tag, text in parsed.headings if tag in {"h2", "h3"}}
                    if not placement_match:
                        blockers.append(
                            f"image asset '{slot}' placement must be 'Before <exact H2/H3>' or 'After <exact H2/H3>'"
                        )
                    elif placement_match.group(1).strip() not in heading_texts:
                        blockers.append(
                            f"image asset '{slot}' placement does not match an exact article H2/H3: "
                            f"{placement_match.group(1).strip()}"
                        )
                item = dict(item)
                item["slot"] = slot
                item["png"] = png_relative
                item["webp"] = relative
                item["alt"] = alt
                item["placement"] = placement
                item["sourceType"] = source_type
                item["visualRole"] = visual_role
                if source_page:
                    item["sourcePage"] = source_page
                if source_image_url:
                    item["sourceImageUrl"] = source_image_url
                item["visualQa"] = {key: visual_qa.get(key) is True for key in IMAGE_VISUAL_QA_KEYS}
                item["sha256"] = file_hash(asset_path)
                asset_by_slot[slot] = item
                asset_source_hashes[f"asset:{relative}"] = item["sha256"]
        except Exception as exc:
            blockers.append(f"could not read image-assets.json: {exc}")

    placeholder_slots: list[str] = []
    for image in parsed.images:
        match = re.fullmatch(r"origin-asset://([a-z0-9]+(?:-[a-z0-9]+)*)", image["src"].strip())
        if match:
            slot = match.group(1)
            placeholder_slots.append(slot)
            asset = asset_by_slot.get(slot)
            if not asset:
                blockers.append(f"article image references an unknown asset slot: {slot}")
            elif image["alt"].strip() != asset["alt"]:
                blockers.append(f"article image alt does not match image-assets.json for slot: {slot}")
    if placeholder_slots and not image_assets:
        blockers.append("article.html uses origin-asset placeholders but image-assets.json is missing")
    for slot in asset_by_slot:
        if slot != "cover" and slot not in placeholder_slots:
            blockers.append(f"image asset is not used in article.html: {slot}")
    if image_assets and "cover" not in asset_by_slot:
        blockers.append("image-assets.json must include a cover slot")
    if image_assets:
        generated_count = sum(
            item.get("sourceType") == "generated-editorial" for item in asset_by_slot.values()
        )
        generated_ratio = generated_count / len(asset_by_slot) if asset_by_slot else 0.0
        product_evidence_count = sum(
            item.get("visualRole") == "product-evidence" for item in asset_by_slot.values()
        )
        origin_owned_count = sum(
            item.get("sourceType") == "origin-owned" for item in asset_by_slot.values()
        )
        if not 6 <= len(asset_by_slot) <= 8:
            blockers.append(f"use 6–8 approved image assets including the cover; found {len(asset_by_slot)}")
        if generated_ratio < 0.60:
            blockers.append(
                f"AI editorial scenes must be the primary image source (at least 60%); found {generated_ratio:.1%}"
            )
        if not 2 <= origin_owned_count <= 3:
            blockers.append(
                f"use 2–3 relevant Origin-owned site images in every article; found {origin_owned_count}"
            )
        if product_evidence_count > 3:
            blockers.append(
                f"use no more than 3 product-evidence images; found {product_evidence_count}"
            )
    else:
        generated_count = 0
        generated_ratio = 0.0
        product_evidence_count = 0
        origin_owned_count = 0

    review_tokens = markdown_article_words(review)
    html_tokens = comparison_words(" ".join(parsed.text_parts))
    if not review_tokens:
        blockers.append("article.md must contain a `## Article` section followed by the reviewed public article")
    elif review_tokens != html_tokens:
        first_difference = next((index for index, pair in enumerate(zip(review_tokens, html_tokens)) if pair[0] != pair[1]), min(len(review_tokens), len(html_tokens)))
        blockers.append(
            f"article.md and article.html public text differ at token {first_difference + 1} "
            f"(Markdown {len(review_tokens)} tokens; HTML {len(html_tokens)} tokens)"
        )
    for field in ["title", "seoTitle", "metaDescription", "handle"]:
        value = str(meta.get(field, ""))
        if value and value not in review:
            blockers.append(f"article.md review pack does not contain meta.{field} exactly")

    if parsed.dangerous:
        blockers.extend(sorted(set(parsed.dangerous)))
    if "h1" in parsed.tags:
        blockers.append("article.html must not contain H1; verify the selected Shopify template renders the title as H1")
    visible_body = re.sub(r"<!--.*?-->", "", body, flags=re.S).lstrip()
    if not re.match(r"<p(?:\s|>)", visible_body, flags=re.I):
        blockers.append("article.html must begin with a readable answer paragraph <p> before headings or wrappers")
    h2s = [text for tag, text in parsed.headings if tag == "h2"]
    if not h2s:
        blockers.append("article.html needs at least one H2")
    first_section_heading = next((tag for tag in parsed.tags if tag in {"h2", "h3"}), None)
    if first_section_heading == "h3":
        blockers.append("article.html must not use H3 before its parent H2")
    if h2s and re.search(r"\bintroduction\b", h2s[0], re.I):
        warnings.append("Remove the Introduction heading and lead with the answer")
    intro_word_count = len(words(" ".join(parsed.intro_parts)))
    if intro_word_count < 35:
        blockers.append(f"opening before first H2 is too thin ({intro_word_count} words)")
    elif intro_word_count > 140:
        warnings.append(f"opening before first H2 is long ({intro_word_count} words)")
    word_count = len(words(" ".join(parsed.text_parts)))
    if content_tier:
        minimum_words, maximum_words = content_range
        if not minimum_words <= word_count <= maximum_words:
            blockers.append(
                f"{content_tier} article must contain {minimum_words}–{maximum_words} words; found {word_count}"
            )

    experience = {"words": 0, "ratio": 0.0, "headings": [], "signals": []}
    try:
        experience = audit_origin_experience(body, word_count)
        if experience["ratio"] < 0.10 or experience["ratio"] > 0.20:
            blockers.append(
                f"Origin experience section must be 10–20% of article words; found {experience['ratio']:.1%}"
            )
    except ValueError as exc:
        blockers.append(str(exc))
    experience_evidence = origin_experience_evidence(sources)
    if not experience_evidence:
        blockers.append(
            "sources.md needs an `## Origin experience evidence` section with a live Origin URL or user-provided evidence"
        )
    if not summary:
        blockers.append("summary.html is empty")
    if len(str(meta.get("seoTitle", ""))) not in range(45, 66):
        warnings.append("SEO title is normally 45–65 characters")
    if len(str(meta.get("metaDescription", ""))) not in range(140, 166):
        warnings.append("meta description is normally 140–165 characters")

    full_text = "\n".join([review, body, summary, json.dumps(meta, ensure_ascii=False), sources, json.dumps(link_plan, ensure_ascii=False)])
    for pattern in PLACEHOLDER_PATTERNS:
        if re.search(pattern, full_text, re.I):
            blockers.append(f"unresolved placeholder or unsafe environment marker: {pattern}")

    normalized_links = []
    for link in parsed.links:
        href = link["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:")):
            continue
        url = canonical_url(href, site_domain)
        normalized_links.append({"url": url, "anchor": link["text"], "section": link["section"]})
        parsed_url = urllib.parse.urlsplit(url)
        if parsed_url.scheme not in {"http", "https"}:
            blockers.append(f"unsupported link scheme: {href}")
        if normalize_host(url) == site_domain and parsed_url.query:
            blockers.append(f"internal link contains query parameters: {url}")
        if not link["text"] or link["text"].lower() in {"click here", "learn more", "read more"}:
            warnings.append(f"non-descriptive anchor: {url}")

    unique_internal = sorted({item["url"] for item in normalized_links if normalize_host(item["url"]) == site_domain})
    unique_products = sorted({url for url in unique_internal if "/products/" in urllib.parse.urlparse(url).path})
    unique_articles = sorted({url for url in unique_internal if "/blogs/" in urllib.parse.urlparse(url).path})
    internal_link_sections = sorted(
        {
            item["section"]
            for item in normalized_links
            if normalize_host(item["url"]) == site_domain
        }
    )
    product_link_sections = sorted(
        {
            item["section"]
            for item in normalized_links
            if normalize_host(item["url"]) == site_domain
            and "/products/" in urllib.parse.urlparse(item["url"]).path
        }
    )
    if len(unique_internal) < 5:
        blockers.append(f"need at least 5 unique internal links; found {len(unique_internal)}")
    if len(unique_products) < 3:
        blockers.append(f"need at least 3 unique product links; found {len(unique_products)}")
    if len(unique_internal) >= 5 and len(internal_link_sections) < 3:
        blockers.append(
            f"internal links are too concentrated; distribute them across at least 3 article sections "
            f"(found {len(internal_link_sections)})"
        )
    if len(unique_products) >= 3 and len(product_link_sections) < 2:
        blockers.append(
            f"product links are too concentrated; distribute them across at least 2 article sections "
            f"(found {len(product_link_sections)})"
        )
    if len(unique_articles) < 2:
        warnings.append(f"normally include at least 2 related article links; found {len(unique_articles)}")
    for asset in asset_by_slot.values():
        if asset.get("sourceType") != "origin-owned":
            continue
        source_page = str(asset.get("sourcePage", ""))
        if source_page and source_page not in unique_internal:
            blockers.append(
                f"Origin-owned image sourcePage must also appear as a contextual internal link: {source_page}"
            )

    if not isinstance(link_plan, list):
        blockers.append("link-plan.json must contain a JSON array")
        link_plan = []
    planned: dict[str, dict] = {}
    for index, item in enumerate(link_plan):
        if not isinstance(item, dict):
            blockers.append(f"link-plan item {index + 1} is not an object")
            continue
        url = canonical_url(str(item.get("url", "")), site_domain)
        planned[url] = item
        if url not in unique_internal:
            blockers.append(f"planned link is absent from article.html: {url}")
        if len(str(item.get("relevance", "")).strip()) < 20:
            blockers.append(f"planned link lacks a useful relevance reason: {url}")
        if not str(item.get("anchor", "")).strip():
            blockers.append(f"planned link lacks anchor text: {url}")
    for url in unique_products:
        if url not in planned or planned[url].get("type") != "product":
            blockers.append(f"product link missing product-type plan entry: {url}")

    source_urls = re.findall(r"https?://[^\s)>]+", sources)
    authoritative = {url.rstrip(".,") for url in source_urls if normalize_host(url) != site_domain}
    if len(authoritative) < 2:
        blockers.append(f"need at least 2 non-Origin authoritative sources; found {len(authoritative)}")
    if not re.search(r"Retrieved:\s*\d{4}-\d{2}-\d{2}", sources):
        warnings.append("sources.md should include `Retrieved: YYYY-MM-DD`")

    for image in parsed.images:
        if not image["src"]:
            blockers.append("image missing src")
        if not image["alt"].strip():
            warnings.append(f"image missing descriptive alt: {image['src'] or '(missing src)'}")
    cover = meta.get("coverImage")
    asset_cover = asset_by_slot.get("cover")
    if not cover and not asset_cover:
        warnings.append("coverImage is not set")
    elif cover and (not cover.get("url") or not cover.get("alt")):
        blockers.append("coverImage requires both url and alt")

    inventory_urls: set[str] = set()
    if args.inventory:
        try:
            inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
            inventory_urls = {canonical_url(item["url"], site_domain) for item in inventory.get("items", [])}
            for url in unique_internal:
                if url not in inventory_urls:
                    blockers.append(f"internal link not found in current sitemap inventory: {url}")
        except Exception as exc:
            blockers.append(f"could not read inventory: {exc}")
    else:
        warnings.append("no sitemap inventory supplied")

    link_checks = []
    if args.check_links:
        for url in unique_internal:
            ok, detail = validate_link(url)
            link_checks.append({"url": url, "ok": ok, "detail": detail})
            if not ok:
                blockers.append(f"link validation failed ({detail}): {url}")
    else:
        warnings.append("live link checks were not requested")

    source_files = list(BASE_SOURCE_FILES)
    if image_manifest_path.is_file() and IMAGE_MANIFEST not in source_files:
        source_files.append(IMAGE_MANIFEST)
    if publication_action == "update" and update_target_path.is_file():
        source_files.append(UPDATE_TARGET_MANIFEST)
    source_hashes = {name: file_hash(bundle / name) for name in source_files}
    source_hashes.update(asset_source_hashes)
    qa = {
        "status": "PASS" if not blockers else "BLOCKED",
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "words": word_count,
            "introWords": intro_word_count,
            "h2": len(h2s),
            "h3": sum(tag == "h3" for tag, _ in parsed.headings),
            "images": len(parsed.images),
            "internalLinks": len(unique_internal),
            "productLinks": len(unique_products),
            "articleLinks": len(unique_articles),
            "internalLinkSections": len(internal_link_sections),
            "productLinkSections": len(product_link_sections),
            "authoritativeSources": len(authoritative),
            "imageAssets": len(image_assets),
            "generatedEditorialImages": generated_count,
            "generatedImageRatio": round(generated_ratio, 4),
            "productEvidenceImages": product_evidence_count,
            "originOwnedSiteImages": origin_owned_count,
            "experienceWords": experience["words"],
        },
        "contentPolicy": {
            "contentTier": content_tier,
            "editorialMode": editorial_mode,
            "wordRange": list(content_range) if content_tier else [],
            "experienceRatio": round(experience["ratio"], 4),
            "experienceHeadings": experience["headings"],
            "experienceSignals": experience["signals"],
            "experienceEvidenceCount": len(experience_evidence),
        },
        "productLinks": unique_products,
        "articleLinks": unique_articles,
        "organization": {
            "blogFilters": blog_filters,
            "blogFilterSource": blog_filter_source,
            "templateSuffix": template_suffix or None,
        },
        "publication": {
            "action": publication_action,
            "updateTarget": {
                "articleId": update_target.get("articleId"),
                "handle": update_target.get("handle"),
                "blogHandle": update_target.get("blogHandle"),
                "capturedAt": update_target.get("capturedAt"),
            } if publication_action == "update" else None,
        },
        "linkChecks": link_checks,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }
    atomic_json(bundle / "qa.json", qa)

    if blockers:
        for stale in [bundle / "approval.json", bundle / "publish-payload.json"]:
            if stale.exists():
                stale.unlink()
        print(json.dumps(qa, indent=2, ensure_ascii=False))
        return 1

    article = {
        "title": str(meta["title"]),
        "handle": handle,
        "author": {"name": str(meta["author"])},
        "body": body,
        "summary": summary,
        "tags": [str(tag) for tag in meta["tags"]],
        "metafields": [
            {"namespace": "global", "key": "title_tag", "type": "single_line_text_field", "value": str(meta["seoTitle"])},
            {"namespace": "global", "key": "description_tag", "type": "single_line_text_field", "value": str(meta["metaDescription"])},
            {
                "namespace": BLOG_FILTER_NAMESPACE,
                "key": BLOG_FILTER_KEY,
                "type": "list.single_line_text_field",
                "value": json.dumps(blog_filters, ensure_ascii=False, separators=(",", ":")),
            },
        ],
    }
    if template_suffix:
        article["templateSuffix"] = template_suffix
    if cover:
        article["image"] = {"url": str(cover["url"]), "altText": str(cover["alt"])}
    elif asset_cover:
        article["image"] = {"url": "origin-asset://cover", "altText": str(asset_cover["alt"])}
    payload = {
        "siteDomain": site_domain,
        "blogHandle": str(meta["blogHandle"]),
        "contentTier": content_tier,
        "editorialMode": editorial_mode,
        "publicationAction": publication_action,
        "article": article,
    }
    if publication_action == "update":
        payload["updateTarget"] = {
            "articleId": str(update_target.get("articleId", "")),
            "handle": str(update_target.get("handle", "")),
            "blogId": str(update_target.get("blogId", "")),
            "blogHandle": str(update_target.get("blogHandle", "")),
            "isPublished": bool(update_target.get("isPublished")),
            "expectedRemoteFingerprint": str(update_target.get("remoteFingerprint", "")),
        }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    short = digest[:8]
    approval: dict[str, object] = {
        "preparedAt": datetime.now(timezone.utc).isoformat(),
        "contentSha256": digest,
        "sourceHashes": source_hashes,
        "publicationAction": publication_action,
    }
    if publication_action == "update":
        approval["updatePhrase"] = f"确认更新 {handle} {short}"
    else:
        approval["livePhrase"] = f"确认发布 {handle} {short}"
        approval["draftPhrase"] = f"确认保存草稿 {handle} {short}"
    atomic_json(bundle / "publish-payload.json", payload)
    atomic_json(bundle / "approval.json", approval)
    result = dict(qa)
    result["approval"] = approval
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

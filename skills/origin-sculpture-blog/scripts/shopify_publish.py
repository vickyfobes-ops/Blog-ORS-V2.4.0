#!/usr/bin/env python3
"""Create or update one hash-approved Shopify article and upload its approved images."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import hmac
import html
import json
import mimetypes
import os
import re
import stat
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    import fcntl
except ImportError:  # pragma: no cover - Shopify state still enforces the limit on non-POSIX systems.
    fcntl = None

BASE_SOURCE_FILES = ["meta.json", "article.md", "article.html", "summary.html", "sources.md", "link-plan.json"]
IMAGE_MANIFEST = "image-assets.json"
UPDATE_TARGET_MANIFEST = "update-target.json"
DEFAULT_CONFIG_FILE = Path.home() / ".config" / "origin-sculpture-blog" / "shopify.env"
CONFIG_KEYS = {
    "SHOPIFY_STORE_DOMAIN",
    "SHOPIFY_ADMIN_ACCESS_TOKEN",
    "SHOPIFY_API_VERSION",
    "SHOPIFY_BLOG_ID",
    "SHOPIFY_PUBLIC_DOMAIN",
    "SHOPIFY_CLIENT_ID",
    "SHOPIFY_CLIENT_SECRET",
    "SHOPIFY_API_KEY",
    "SHOPIFY_API_SECRET",
    "SHOPIFY_ARTICLE_TEMPLATE_SUFFIXES",
    "SHOPIFY_MAX_LIVE_ARTICLES_PER_DAY",
}
USER_AGENT = "OriginSculptureBlogSkill/2.4.3 (+https://originsculpture.com)"
BLOG_FILTER_NAMESPACE = "custom"
BLOG_FILTER_KEY = "blog_filter"
DEFAULT_MAX_LIVE_ARTICLES_PER_DAY = 3
MAX_ALLOWED_LIVE_ARTICLES_PER_DAY = 10
MAX_THROTTLE_RETRIES = 5
MAX_THROTTLE_WAIT_SECONDS = 30.0


def secure_equal(left: object, right: object) -> bool:
    return hmac.compare_digest(str(left).encode("utf-8"), str(right).encode("utf-8"))


def normalize_host(value: str) -> str:
    parsed = urllib.parse.urlparse(value if "://" in value else f"https://{value}")
    return parsed.netloc.lower().split(":", 1)[0].removeprefix("www.")


def atomic_json(path: Path, payload: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def safe_bundle_path(bundle: Path, relative: str) -> Path:
    candidate = (bundle / relative).resolve()
    if bundle != candidate and bundle not in candidate.parents:
        raise RuntimeError(f"Asset path escapes the bundle: {relative}")
    return candidate


def load_protected_config() -> Path | None:
    configured = os.environ.get("ORIGIN_SHOPIFY_ENV_FILE", "").strip()
    path = Path(configured).expanduser() if configured else DEFAULT_CONFIG_FILE
    if not path.is_file():
        return None
    if os.name == "posix" and stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise RuntimeError(f"Shopify config permissions are too broad: {path}. Use chmod 600.")
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            raise RuntimeError(f"Invalid line in protected Shopify config: {path}")
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if name not in CONFIG_KEYS:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(name, value)
    return path


def acquire_client_credentials_token(store: str, client_id: str, client_secret: str) -> str:
    endpoint = f"https://{store}/admin/oauth/access_token"
    form = urllib.parse.urlencode(
        {"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret}
    ).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=form,
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": USER_AGENT},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        safe_body = exc.read().decode("utf-8", "replace")[:1000]
        raise RuntimeError(f"Shopify token request failed with HTTP {exc.code}: {safe_body}") from exc
    token = str(result.get("access_token", "")).strip()
    if not token:
        raise RuntimeError("Shopify client-credentials response did not contain an access token")
    return token


def environment() -> tuple[str, str, str, Path | None]:
    config_path = load_protected_config()
    store = normalize_host(os.environ.get("SHOPIFY_STORE_DOMAIN", "").strip())
    version = os.environ.get("SHOPIFY_API_VERSION", "").strip()
    token = os.environ.get("SHOPIFY_ADMIN_ACCESS_TOKEN", "").strip()
    if not store or not version:
        missing = []
        if not store:
            missing.append("SHOPIFY_STORE_DOMAIN")
        if not version:
            missing.append("SHOPIFY_API_VERSION")
        raise RuntimeError(f"Missing Shopify configuration: {', '.join(missing)}")
    if not token:
        client_id = (
            os.environ.get("SHOPIFY_CLIENT_ID", "").strip()
            or os.environ.get("SHOPIFY_API_KEY", "").strip()
        )
        client_secret = (
            os.environ.get("SHOPIFY_CLIENT_SECRET", "").strip()
            or os.environ.get("SHOPIFY_API_SECRET", "").strip()
        )
        if not client_id or not client_secret:
            raise RuntimeError(
                "Configure SHOPIFY_ADMIN_ACCESS_TOKEN, SHOPIFY_CLIENT_ID/SHOPIFY_CLIENT_SECRET, "
                "or Shopify CLI's SHOPIFY_API_KEY/SHOPIFY_API_SECRET"
            )
        token = acquire_client_credentials_token(store, client_id, client_secret)
    return store, token, version, config_path


def throttle_delay(attempt: int, retry_after: object = None) -> float:
    try:
        requested = float(retry_after) if retry_after not in {None, ""} else 0.0
    except (TypeError, ValueError):
        requested = 0.0
    exponential = float(2**attempt)
    return min(MAX_THROTTLE_WAIT_SECONDS, max(requested, exponential))


def throttled_errors(errors: object) -> bool:
    if not isinstance(errors, list) or not errors:
        return False
    for error in errors:
        if not isinstance(error, dict):
            return False
        code = str((error.get("extensions") or {}).get("code", "")).upper()
        message = str(error.get("message", "")).lower()
        if code != "THROTTLED" and "throttl" not in message:
            return False
    return True


def graphql(
    store: str,
    token: str,
    version: str,
    query: str,
    variables: dict,
    *,
    retry_throttled: bool = True,
) -> dict:
    endpoint = f"https://{store}/admin/api/{version}/graphql.json"
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    for attempt in range(MAX_THROTTLE_RETRIES + 1):
        request = urllib.request.Request(
            endpoint,
            data=body,
            headers={"Content-Type": "application/json", "X-Shopify-Access-Token": token, "User-Agent": USER_AGENT},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            safe_body = exc.read().decode("utf-8", "replace")[:1000]
            if exc.code == 429 and retry_throttled and attempt < MAX_THROTTLE_RETRIES:
                delay = throttle_delay(attempt, exc.headers.get("Retry-After"))
                print(
                    f"Shopify API throttled the request; retrying in {delay:g}s "
                    f"({attempt + 1}/{MAX_THROTTLE_RETRIES}).",
                    file=sys.stderr,
                )
                time.sleep(delay)
                continue
            raise RuntimeError(f"Shopify HTTP {exc.code}: {safe_body}") from exc
        errors = result.get("errors")
        if errors and throttled_errors(errors) and retry_throttled and attempt < MAX_THROTTLE_RETRIES:
            delay = throttle_delay(attempt)
            print(
                f"Shopify GraphQL throttled the request; retrying in {delay:g}s "
                f"({attempt + 1}/{MAX_THROTTLE_RETRIES}).",
                file=sys.stderr,
            )
            time.sleep(delay)
            continue
        if errors:
            raise RuntimeError(f"Shopify GraphQL errors: {json.dumps(errors, ensure_ascii=False)}")
        return result.get("data", {})
    raise RuntimeError("Shopify API throttle retry budget was exhausted")


ARTICLE_STATE_QUERY = """
query ArticleState($id: ID!) {
  node(id: $id) {
    ... on Article {
      id
      title
      handle
      body
      summary
      tags
      templateSuffix
      isPublished
      publishedAt
      author { name }
      blog { id title handle }
      image { altText originalSrc }
      metafields(first: 20) { nodes { namespace key type value } }
    }
  }
}
"""


def normalized_remote_article(article: dict) -> dict:
    if not article or not article.get("id"):
        raise RuntimeError("Shopify article target could not be read")
    relevant_metafields = []
    for item in (article.get("metafields") or {}).get("nodes", []):
        identity = (str(item.get("namespace", "")), str(item.get("key", "")))
        if identity not in {
            ("global", "title_tag"),
            ("global", "description_tag"),
            (BLOG_FILTER_NAMESPACE, BLOG_FILTER_KEY),
        }:
            continue
        relevant_metafields.append(
            {
                "namespace": identity[0],
                "key": identity[1],
                "type": str(item.get("type", "")),
                "value": str(item.get("value", "")),
            }
        )
    relevant_metafields.sort(key=lambda item: (item["namespace"], item["key"]))
    image_data = article.get("image") or {}
    blog = article.get("blog") or {}
    author = article.get("author") or {}
    return {
        "id": str(article.get("id", "")),
        "title": str(article.get("title", "")),
        "handle": str(article.get("handle", "")),
        "body": str(article.get("body", "")),
        "summary": str(article.get("summary", "")),
        "tags": [str(value) for value in (article.get("tags") or [])],
        "templateSuffix": str(article.get("templateSuffix", "") or ""),
        "isPublished": bool(article.get("isPublished")),
        "publishedAt": article.get("publishedAt"),
        "author": str(author.get("name", "")),
        "blog": {
            "id": str(blog.get("id", "")),
            "title": str(blog.get("title", "")),
            "handle": str(blog.get("handle", "")),
        },
        "image": {
            "altText": str(image_data.get("altText", "")),
            "originalSrc": str(image_data.get("originalSrc", "")),
        },
        "metafields": relevant_metafields,
    }


def remote_article_fingerprint(article: dict) -> str:
    normalized = normalized_remote_article(article)
    canonical = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def read_remote_article(store: str, token: str, version: str, article_id: str) -> dict:
    node = graphql(store, token, version, ARTICLE_STATE_QUERY, {"id": article_id}).get("node")
    if not isinstance(node, dict) or str(node.get("id", "")) != article_id:
        raise RuntimeError(f"Shopify article target is missing or inaccessible: {article_id}")
    return node


def store_identity(store: str, token: str, version: str) -> dict:
    query = """
query StoreIdentity {
  shop { name myshopifyDomain ianaTimezone primaryDomain { host url } }
  currentAppInstallation { accessScopes { handle } }
}
"""
    data = graphql(store, token, version, query, {})
    shop = data.get("shop") or {}
    if not shop.get("myshopifyDomain"):
        raise RuntimeError("Could not verify the Shopify store identity")
    scopes = sorted(
        str(item.get("handle"))
        for item in (data.get("currentAppInstallation") or {}).get("accessScopes", [])
        if item.get("handle")
    )
    return {"shop": shop, "scopes": scopes}


def verify_target_store(store: str, token: str, version: str, public_domain: str) -> dict:
    identity = store_identity(store, token, version)
    shop = identity["shop"]
    actual_admin = normalize_host(str(shop.get("myshopifyDomain", "")))
    if actual_admin != store:
        raise RuntimeError(f"Configured store '{store}' resolved to a different Shopify store '{actual_admin}'")
    primary = normalize_host(str((shop.get("primaryDomain") or {}).get("host", "")))
    approved_alias = normalize_host(os.environ.get("SHOPIFY_PUBLIC_DOMAIN", "").strip())
    if primary != public_domain and approved_alias != public_domain:
        raise RuntimeError(
            f"Shopify primary domain '{primary}' does not match approved public domain '{public_domain}'. "
            f"After verifying the mapping, set SHOPIFY_PUBLIC_DOMAIN={public_domain}."
        )
    return identity


def list_blog_nodes(store: str, token: str, version: str) -> list[dict]:
    query = "query Blogs { blogs(first: 50) { nodes { id title handle } } }"
    return graphql(store, token, version, query, {}).get("blogs", {}).get("nodes", [])


def blog_filter_definition(store: str, token: str, version: str) -> dict:
    query = """
query BlogFilterDefinition {
  metafieldDefinitions(first: 10, ownerType: ARTICLE, namespace: "custom", key: "blog_filter") {
    nodes { id name namespace key type { name } validations { name value } }
  }
}
"""
    nodes = graphql(store, token, version, query, {}).get("metafieldDefinitions", {}).get("nodes", [])
    matches = [node for node in nodes if node.get("namespace") == BLOG_FILTER_NAMESPACE and node.get("key") == BLOG_FILTER_KEY]
    if len(matches) != 1:
        raise RuntimeError("Expected one ARTICLE metafield definition for custom.blog_filter")
    definition = matches[0]
    choices: list[str] = []
    for validation in definition.get("validations") or []:
        if validation.get("name") == "choices":
            try:
                parsed = json.loads(str(validation.get("value", "[]")))
            except json.JSONDecodeError as exc:
                raise RuntimeError("Shopify Blog Filter choices are not valid JSON") from exc
            if isinstance(parsed, list):
                choices = [str(value) for value in parsed]
    return {"definition": definition, "choices": choices}


def configured_template_suffixes() -> list[str]:
    raw = os.environ.get("SHOPIFY_ARTICLE_TEMPLATE_SUFFIXES", "")
    return sorted({value.strip() for value in raw.split(",") if value.strip()})


def configured_daily_publish_limit() -> int:
    raw = os.environ.get("SHOPIFY_MAX_LIVE_ARTICLES_PER_DAY", "").strip()
    if not raw:
        return DEFAULT_MAX_LIVE_ARTICLES_PER_DAY
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError("SHOPIFY_MAX_LIVE_ARTICLES_PER_DAY must be an integer") from exc
    if not 1 <= value <= MAX_ALLOWED_LIVE_ARTICLES_PER_DAY:
        raise RuntimeError(
            f"SHOPIFY_MAX_LIVE_ARTICLES_PER_DAY must be between 1 and {MAX_ALLOWED_LIVE_ARTICLES_PER_DAY}"
        )
    return value


def parse_shopify_datetime(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Shopify DateTime is missing a timezone")
    return parsed


def daily_publish_status(
    store: str,
    token: str,
    version: str,
    *,
    now: datetime | None = None,
    limit: int | None = None,
) -> dict:
    effective_limit = limit if limit is not None else configured_daily_publish_limit()
    if not 1 <= effective_limit <= MAX_ALLOWED_LIVE_ARTICLES_PER_DAY:
        raise RuntimeError(f"Daily live-article limit must be between 1 and {MAX_ALLOWED_LIVE_ARTICLES_PER_DAY}")
    query = """
query DailyPublishStatus {
  shop { ianaTimezone }
  articles(first: 25, sortKey: PUBLISHED_AT, reverse: true) {
    nodes { id handle title isPublished publishedAt }
  }
}
"""
    data = graphql(store, token, version, query, {})
    timezone_name = str((data.get("shop") or {}).get("ianaTimezone", "")).strip()
    try:
        shop_timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise RuntimeError(f"Shopify returned an unknown store timezone: {timezone_name or '(missing)'}") from exc
    checked_at = now or datetime.now(timezone.utc)
    if checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=timezone.utc)
    shop_date = checked_at.astimezone(shop_timezone).date()
    published_today = []
    for node in (data.get("articles") or {}).get("nodes", []):
        if not node.get("isPublished") or not node.get("publishedAt"):
            continue
        try:
            published_at = parse_shopify_datetime(node["publishedAt"])
        except (TypeError, ValueError):
            continue
        if published_at.astimezone(shop_timezone).date() == shop_date:
            published_today.append(
                {
                    "id": node.get("id"),
                    "handle": node.get("handle"),
                    "title": node.get("title"),
                    "publishedAt": node.get("publishedAt"),
                }
            )
    count = len(published_today)
    return {
        "timezone": timezone_name,
        "date": shop_date.isoformat(),
        "limit": effective_limit,
        "publishedCount": count,
        "remaining": max(effective_limit - count, 0),
        "publishedToday": published_today,
    }


def enforce_daily_publish_limit(store: str, token: str, version: str) -> dict:
    status = daily_publish_status(store, token, version)
    if status["publishedCount"] >= status["limit"]:
        raise RuntimeError(
            f"Daily live-article limit reached for {status['date']} in {status['timezone']}: "
            f"{status['publishedCount']}/{status['limit']}. Save as draft or publish after the store date changes."
        )
    return status


@contextmanager
def live_publish_lock(store: str):
    lock_directory = DEFAULT_CONFIG_FILE.parent
    lock_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "posix":
        os.chmod(lock_directory, 0o700)
    lock_name = re.sub(r"[^a-z0-9.-]+", "-", store.lower()) + ".live-publish.lock"
    lock_path = lock_directory / lock_name
    with lock_path.open("a+", encoding="utf-8") as handle:
        if os.name == "posix":
            os.chmod(lock_path, 0o600)
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def article_organization(article: dict) -> dict:
    filters: list[str] = []
    for metafield in article.get("metafields") or []:
        if metafield.get("namespace") == BLOG_FILTER_NAMESPACE and metafield.get("key") == BLOG_FILTER_KEY:
            try:
                parsed = json.loads(str(metafield.get("value", "[]")))
            except json.JSONDecodeError as exc:
                raise RuntimeError("Approved Blog Filter value is not valid JSON") from exc
            if not isinstance(parsed, list) or not parsed:
                raise RuntimeError("Approved Blog Filter must contain at least one value")
            filters = [str(value) for value in parsed]
    if not filters:
        raise RuntimeError("Approved article is missing custom.blog_filter")
    return {"blogFilters": filters, "templateSuffix": str(article.get("templateSuffix", "")).strip() or None}


def verify_article_organization(store: str, token: str, version: str, article: dict) -> dict:
    organization = article_organization(article)
    live = blog_filter_definition(store, token, version)
    field_type = str((live.get("definition") or {}).get("type", {}).get("name", ""))
    if field_type != "list.single_line_text_field":
        raise RuntimeError(f"custom.blog_filter has unexpected Shopify type: {field_type or '(missing)'}")
    choices = live.get("choices") or []
    unknown = [value for value in organization["blogFilters"] if value not in choices]
    if unknown:
        raise RuntimeError(f"Approved Blog Filter value is not allowed by Shopify: {', '.join(unknown)}")
    suffix = organization["templateSuffix"]
    configured = configured_template_suffixes()
    if suffix and suffix not in configured:
        raise RuntimeError(
            f"Template suffix '{suffix}' is not in SHOPIFY_ARTICLE_TEMPLATE_SUFFIXES. "
            "Confirm it exists in the live theme before publishing."
        )
    organization["availableBlogFilters"] = choices
    organization["configuredTemplateSuffixes"] = configured
    organization["templateMode"] = "custom" if suffix else "default"
    return organization


def list_blogs() -> int:
    store, token, version, config_path = environment()
    identity = store_identity(store, token, version)
    result = {
        "store": identity["shop"],
        "scopes": identity["scopes"],
        "blogs": list_blog_nodes(store, token, version),
        "configSource": str(config_path) if config_path else "environment",
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def verify_store(bundle: Path | None) -> int:
    store, token, version, config_path = environment()
    public_domain = ""
    needs_files = False
    if bundle:
        meta = json.loads((bundle / "meta.json").read_text(encoding="utf-8"))
        public_domain = normalize_host(str(meta.get("siteDomain", "")))
        needs_files = (bundle / IMAGE_MANIFEST).is_file()
    if public_domain:
        identity = verify_target_store(store, token, version, public_domain)
    else:
        identity = store_identity(store, token, version)
    required_scopes = {"read_content", "write_content"}
    if needs_files:
        required_scopes.update({"read_files", "write_files"})
    missing_scopes = sorted(required_scopes - set(identity["scopes"]))
    daily_status = daily_publish_status(store, token, version)
    result = {
        "status": "PASS" if not missing_scopes else "BLOCKED",
        "store": identity["shop"],
        "apiVersion": version,
        "scopes": identity["scopes"],
        "requiredScopes": sorted(required_scopes),
        "missingScopes": missing_scopes,
        "blogs": list_blog_nodes(store, token, version),
        "organization": {
            "availableBlogFilters": blog_filter_definition(store, token, version)["choices"],
            "configuredTemplateSuffixes": configured_template_suffixes(),
            "defaultTemplateAvailable": True,
        },
        "dailyPublishProtection": daily_status,
        "throttleProtection": {
            "automaticRetries": MAX_THROTTLE_RETRIES,
            "maximumWaitSeconds": MAX_THROTTLE_WAIT_SECONDS,
            "articleCreateBlindRetry": False,
            "articleUpdateBlindRetry": False,
        },
        "configSource": str(config_path) if config_path else "environment",
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not missing_scopes else 1


def capture_update_target(bundle: Path) -> int:
    meta = json.loads((bundle / "meta.json").read_text(encoding="utf-8"))
    public_domain = normalize_host(str(meta.get("siteDomain", "")))
    handle = str(meta.get("handle", "")).strip()
    blog_handle = str(meta.get("blogHandle", "")).strip()
    if not public_domain or not handle or not blog_handle:
        raise RuntimeError("meta.json needs siteDomain, handle, and blogHandle before capturing an update target")
    store, token, version, _ = environment()
    identity = verify_target_store(store, token, version, public_domain)
    missing_scopes = sorted({"read_content", "write_content"} - set(identity["scopes"]))
    if missing_scopes:
        raise RuntimeError(f"Shopify app is missing required scopes: {', '.join(missing_scopes)}")
    query = """
query ExistingArticle($query: String!) {
  articles(first: 10, query: $query) {
    nodes { id title handle isPublished blog { id title handle } }
  }
}
"""
    nodes = graphql(store, token, version, query, {"query": f"handle:{handle}"}).get("articles", {}).get("nodes", [])
    matches = [
        node for node in nodes
        if str(node.get("handle", "")) == handle
        and str((node.get("blog") or {}).get("handle", "")) == blog_handle
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one live Shopify article at /blogs/{blog_handle}/{handle}; found {len(matches)}"
        )
    article = read_remote_article(store, token, version, str(matches[0]["id"]))
    normalized = normalized_remote_article(article)
    result = {
        "capturedAt": datetime.now(timezone.utc).isoformat(),
        "articleId": normalized["id"],
        "handle": normalized["handle"],
        "blogId": normalized["blog"]["id"],
        "blogHandle": normalized["blog"]["handle"],
        "isPublished": normalized["isPublished"],
        "publishedAt": normalized["publishedAt"],
        "remoteFingerprint": remote_article_fingerprint(article),
        "publicUrl": f"https://{public_domain}/blogs/{normalized['blog']['handle']}/{normalized['handle']}",
    }
    atomic_json(bundle / UPDATE_TARGET_MANIFEST, result)
    print(json.dumps({"status": "UPDATE_TARGET_CAPTURED", **result}, indent=2, ensure_ascii=False))
    return 0


def verify_source_hashes(bundle: Path, expected: dict[str, str]) -> None:
    for name in BASE_SOURCE_FILES:
        if name not in expected:
            raise RuntimeError(f"Approval is missing a source hash for: {name}")
    for name, expected_hash in expected.items():
        if name.startswith("asset:"):
            path = safe_bundle_path(bundle, name.removeprefix("asset:"))
        else:
            path = safe_bundle_path(bundle, name)
        if not path.is_file():
            raise RuntimeError(f"Approved source file is missing: {name}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if not secure_equal(actual, expected_hash):
            raise RuntimeError(f"Source changed after approval preparation: {name}")


def resolve_blog_id(store: str, token: str, version: str, handle: str) -> str:
    configured = os.environ.get("SHOPIFY_BLOG_ID", "").strip()
    if configured:
        return configured
    nodes = list_blog_nodes(store, token, version)
    matches = [node for node in nodes if node.get("handle") == handle]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one Shopify blog with handle '{handle}', found {len(matches)}. Set SHOPIFY_BLOG_ID explicitly."
        )
    return str(matches[0]["id"])


def load_assets(bundle: Path) -> list[dict]:
    manifest = bundle / IMAGE_MANIFEST
    if not manifest.is_file():
        return []
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise RuntimeError("image-assets.json must contain a JSON array")
    assets = []
    seen = set()
    for item in raw:
        slot = str(item.get("slot", "")).strip()
        relative = str(item.get("webp", "")).strip()
        alt = str(item.get("alt", "")).strip()
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slot) or slot in seen:
            raise RuntimeError(f"Invalid or duplicate image asset slot: {slot}")
        path = safe_bundle_path(bundle, relative)
        if not path.is_file() or path.suffix.lower() != ".webp" or not alt:
            raise RuntimeError(f"Invalid approved image asset: {slot}")
        seen.add(slot)
        assets.append({"slot": slot, "path": path, "alt": alt, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return assets


def multipart_upload(url: str, parameters: list[dict], asset: dict) -> None:
    boundary = f"----OriginSculpture{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for parameter in parameters:
        name = str(parameter.get("name", ""))
        value = str(parameter.get("value", ""))
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        chunks.append(value.encode("utf-8"))
        chunks.append(b"\r\n")
    filename = asset["filename"]
    mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    chunks.append(f"--{boundary}\r\n".encode())
    chunks.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
    chunks.append(f"Content-Type: {mime_type}\r\n\r\n".encode())
    chunks.append(asset["path"].read_bytes())
    chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    body = b"".join(chunks)
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": USER_AGENT},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            if not 200 <= response.status < 300:
                raise RuntimeError(f"Staged upload returned HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        safe_body = exc.read().decode("utf-8", "replace")[:1000]
        raise RuntimeError(f"Staged upload failed with HTTP {exc.code}: {safe_body}") from exc


def wait_for_images(store: str, token: str, version: str, ids: list[str], timeout_seconds: int = 90) -> list[dict]:
    query = """
query FileNodes($ids: [ID!]!) {
  nodes(ids: $ids) {
    id
    ... on MediaImage { fileStatus alt image { url width height } }
  }
}
"""
    deadline = time.monotonic() + timeout_seconds
    while True:
        nodes = graphql(store, token, version, query, {"ids": ids}).get("nodes", [])
        by_id = {str(node.get("id")): node for node in nodes if node}
        failed = [node for node in by_id.values() if node.get("fileStatus") == "FAILED"]
        if failed:
            raise RuntimeError(f"Shopify image processing failed for: {[node.get('id') for node in failed]}")
        if len(by_id) == len(ids) and all(by_id[item].get("fileStatus") == "READY" and (by_id[item].get("image") or {}).get("url") for item in ids):
            return [by_id[item] for item in ids]
        if time.monotonic() >= deadline:
            raise RuntimeError("Timed out while Shopify processed uploaded images")
        time.sleep(2)


def upload_assets(store: str, token: str, version: str, bundle: Path, handle: str, digest: str, assets: list[dict]) -> dict:
    cache_path = bundle / "asset-upload-result.json"
    cached_slots: dict = {}
    if cache_path.is_file():
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        cached_slots = cached.get("assets", {}) if isinstance(cached.get("assets"), dict) else {}
        if secure_equal(cached.get("contentSha256", ""), digest) and all(
            cached_slots.get(asset["slot"], {}).get("url")
            and secure_equal(cached_slots.get(asset["slot"], {}).get("sha256", ""), asset["sha256"])
            for asset in assets
        ):
            return cached

    reused_assets = {
        asset["slot"]: cached_slots[asset["slot"]]
        for asset in assets
        if cached_slots.get(asset["slot"], {}).get("url")
        and secure_equal(cached_slots.get(asset["slot"], {}).get("sha256", ""), asset["sha256"])
    }
    pending_assets = [asset for asset in assets if asset["slot"] not in reused_assets]
    if not pending_assets:
        result = {
            "uploadedAt": datetime.now(timezone.utc).isoformat(),
            "contentSha256": digest,
            "assets": reused_assets,
        }
        atomic_json(cache_path, result)
        return result

    prepared_assets = []
    staged_inputs = []
    for asset in pending_assets:
        filename = f"origin-{handle}-{asset['slot']}-{asset['sha256'][:10]}.webp"
        prepared = dict(asset)
        prepared["filename"] = filename
        prepared_assets.append(prepared)
        staged_inputs.append(
            {
                "filename": filename,
                "mimeType": "image/webp",
                "resource": "FILE",
                "httpMethod": "POST",
                "fileSize": str(asset["path"].stat().st_size),
            }
        )
    staged_mutation = """
mutation StagedUploads($input: [StagedUploadInput!]!) {
  stagedUploadsCreate(input: $input) {
    stagedTargets { url resourceUrl parameters { name value } }
    userErrors { field message }
  }
}
"""
    staged = graphql(store, token, version, staged_mutation, {"input": staged_inputs}).get("stagedUploadsCreate", {})
    if staged.get("userErrors"):
        raise RuntimeError(f"Shopify rejected staged uploads: {json.dumps(staged['userErrors'], ensure_ascii=False)}")
    targets = staged.get("stagedTargets") or []
    if len(targets) != len(prepared_assets):
        raise RuntimeError("Shopify returned an unexpected number of staged upload targets")
    for asset, target in zip(prepared_assets, targets):
        multipart_upload(str(target["url"]), target.get("parameters") or [], asset)

    files_input = [
        {
            "alt": asset["alt"],
            "contentType": "IMAGE",
            "originalSource": str(target["resourceUrl"]),
            "filename": asset["filename"],
        }
        for asset, target in zip(prepared_assets, targets)
    ]
    create_mutation = """
mutation CreateFiles($files: [FileCreateInput!]!) {
  fileCreate(files: $files) {
    files { id fileStatus alt ... on MediaImage { image { url width height } } }
    userErrors { code field message }
  }
}
"""
    created = graphql(store, token, version, create_mutation, {"files": files_input}).get("fileCreate", {})
    if created.get("userErrors"):
        raise RuntimeError(f"Shopify rejected image files: {json.dumps(created['userErrors'], ensure_ascii=False)}")
    files = created.get("files") or []
    if len(files) != len(prepared_assets) or any(not item.get("id") for item in files):
        raise RuntimeError("Shopify returned an unexpected image-file result")
    ready = wait_for_images(store, token, version, [str(item["id"]) for item in files])
    result_assets = dict(reused_assets)
    for asset, node in zip(prepared_assets, ready):
        image_data = node.get("image") or {}
        result_assets[asset["slot"]] = {
            "id": node["id"],
            "url": image_data["url"],
            "width": image_data.get("width"),
            "height": image_data.get("height"),
            "alt": asset["alt"],
            "sha256": asset["sha256"],
        }
    result = {
        "uploadedAt": datetime.now(timezone.utc).isoformat(),
        "contentSha256": digest,
        "assets": result_assets,
    }
    atomic_json(cache_path, result)
    return result


def render_article_assets(article: dict, uploaded: dict) -> dict:
    rendered = dict(article)
    rendered["body"] = str(rendered.get("body", ""))
    slot_map = uploaded.get("assets", {})
    for slot, item in slot_map.items():
        placeholder = f"origin-asset://{slot}"
        rendered["body"] = rendered["body"].replace(placeholder, html.escape(str(item["url"]), quote=True))
    image = rendered.get("image")
    if isinstance(image, dict) and str(image.get("url", "")).startswith("origin-asset://"):
        slot = str(image["url"]).removeprefix("origin-asset://")
        if slot not in slot_map:
            raise RuntimeError(f"Missing uploaded cover asset: {slot}")
        rendered["image"] = {"url": str(slot_map[slot]["url"]), "altText": str(image.get("altText", ""))}
    if "origin-asset://" in rendered["body"] or "origin-asset://" in json.dumps(rendered.get("image", {})):
        raise RuntimeError("Unresolved image asset placeholder remains before publication")
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--confirm")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list-blogs", action="store_true")
    parser.add_argument("--verify-store", action="store_true")
    parser.add_argument("--capture-update-target", action="store_true")
    args = parser.parse_args()

    try:
        if args.list_blogs:
            return list_blogs()
        if args.verify_store:
            return verify_store(args.bundle.resolve() if args.bundle else None)
        if not args.bundle:
            raise RuntimeError("--bundle is required")
        bundle = args.bundle.resolve()
        if args.capture_update_target:
            return capture_update_target(bundle)
        approval = json.loads((bundle / "approval.json").read_text(encoding="utf-8"))
        payload = json.loads((bundle / "publish-payload.json").read_text(encoding="utf-8"))
        qa = json.loads((bundle / "qa.json").read_text(encoding="utf-8"))
        if qa.get("status") != "PASS" or qa.get("blockers"):
            raise RuntimeError("qa.json is not a clean PASS")
        verify_source_hashes(bundle, approval.get("sourceHashes", {}))
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        digest = hashlib.sha256(canonical).hexdigest()
        if not secure_equal(digest, approval.get("contentSha256", "")):
            raise RuntimeError("publish-payload.json does not match approval.json")
        assets = load_assets(bundle)
        publication_action = str(payload.get("publicationAction", "create")).strip().lower()
        if publication_action not in {"create", "update"}:
            raise RuntimeError("publish-payload.json has an invalid publicationAction")

        safe_summary = {
            "siteDomain": payload.get("siteDomain"),
            "blogHandle": payload.get("blogHandle"),
            "contentTier": payload.get("contentTier"),
            "publicationAction": publication_action,
            "title": payload.get("article", {}).get("title"),
            "handle": payload.get("article", {}).get("handle"),
            "contentSha256": digest,
            "imageAssets": len(assets),
            "organization": article_organization(payload.get("article", {})),
            "livePhrase": approval.get("livePhrase"),
            "draftPhrase": approval.get("draftPhrase"),
            "updatePhrase": approval.get("updatePhrase"),
            "dailyLiveArticleLimit": DEFAULT_MAX_LIVE_ARTICLES_PER_DAY,
        }
        if args.dry_run:
            load_protected_config()
            safe_summary["dailyLiveArticleLimit"] = configured_daily_publish_limit()
            print(json.dumps({"status": "DRY_RUN", **safe_summary}, indent=2, ensure_ascii=False))
            return 0

        confirmation = args.confirm or ""
        live = publication_action == "create" and secure_equal(confirmation, approval.get("livePhrase", ""))
        draft = publication_action == "create" and secure_equal(confirmation, approval.get("draftPhrase", ""))
        update = publication_action == "update" and secure_equal(confirmation, approval.get("updatePhrase", ""))
        if not (live or draft or update):
            expected = "update phrase" if publication_action == "update" else "live or draft phrase"
            raise RuntimeError(f"Confirmation does not exactly match the current {expected}")

        store, token, version, _ = environment()
        target = normalize_host(str(payload.get("siteDomain", "")))
        identity = verify_target_store(store, token, version, target)
        required_scopes = {"read_content", "write_content"}
        if assets:
            required_scopes.update({"read_files", "write_files"})
        missing_scopes = sorted(required_scopes - set(identity["scopes"]))
        if missing_scopes:
            raise RuntimeError(f"Shopify app is missing required scopes: {', '.join(missing_scopes)}")

        approved_article = dict(payload["article"])
        organization = verify_article_organization(store, token, version, approved_article)
        handle = str(approved_article["handle"])
        duplicate_query = "query Existing($query: String!) { articles(first: 2, query: $query) { nodes { id title handle isPublished blog { id handle } } } }"
        update_target: dict = {}
        expected_remote_fingerprint = ""
        if update:
            update_target = payload.get("updateTarget") or {}
            article_id = str(update_target.get("articleId", ""))
            expected_remote_fingerprint = str(update_target.get("expectedRemoteFingerprint", ""))
            if not re.fullmatch(r"gid://shopify/Article/\d+", article_id):
                raise RuntimeError("Approved update target has an invalid Shopify article ID")
            current_article = read_remote_article(store, token, version, article_id)
            current_normalized = normalized_remote_article(current_article)
            if current_normalized["handle"] != handle:
                raise RuntimeError("Shopify update target handle no longer matches the approved article")
            if current_normalized["blog"]["handle"] != str(payload["blogHandle"]):
                raise RuntimeError("Shopify update target blog no longer matches the approved article")
            if not secure_equal(remote_article_fingerprint(current_article), expected_remote_fingerprint):
                raise RuntimeError(
                    "Shopify article changed after the update target was captured; refresh the review bundle and approval phrase"
                )
        else:
            existing = graphql(store, token, version, duplicate_query, {"query": f"handle:{handle}"}).get("articles", {}).get("nodes", [])
            if existing:
                raise RuntimeError(f"Article handle already exists; create aborted: {json.dumps(existing, ensure_ascii=False)}")

        daily_protection = None
        if live:
            daily_protection = enforce_daily_publish_limit(store, token, version)

        uploaded = {"assets": {}}
        if assets:
            uploaded = upload_assets(store, token, version, bundle, handle, digest, assets)
        article = render_article_assets(approved_article, uploaded)
        updated_remote_fingerprint = None
        if update:
            if "templateSuffix" not in article:
                article["templateSuffix"] = ""
            mutation = """
mutation UpdateArticle($id: ID!, $article: ArticleUpdateInput!) {
  articleUpdate(id: $id, article: $article) {
    article { id title handle isPublished publishedAt blog { id title handle } image { altText originalSrc } }
    userErrors { code field message }
  }
}
"""
            article_id = str(update_target["articleId"])
            with live_publish_lock(store):
                current_article = read_remote_article(store, token, version, article_id)
                if not secure_equal(remote_article_fingerprint(current_article), expected_remote_fingerprint):
                    raise RuntimeError(
                        "Shopify article changed immediately before update; refresh the review bundle and approval phrase"
                    )
                mutation_result = graphql(
                    store,
                    token,
                    version,
                    mutation,
                    {"id": article_id, "article": article},
                    retry_throttled=False,
                ).get("articleUpdate", {})
            if mutation_result.get("userErrors"):
                raise RuntimeError(
                    f"Shopify rejected article update: {json.dumps(mutation_result['userErrors'], ensure_ascii=False)}"
                )
            record = mutation_result.get("article")
            if not record:
                raise RuntimeError("Shopify returned no updated article record")
            updated_article = read_remote_article(store, token, version, article_id)
            updated_remote_fingerprint = remote_article_fingerprint(updated_article)
            if str(updated_article.get("handle", "")) != handle:
                raise RuntimeError("Shopify returned an unexpected handle after article update")
        else:
            article["blogId"] = resolve_blog_id(store, token, version, str(payload["blogHandle"]))
            article["isPublished"] = live
            mutation = """
mutation CreateArticle($article: ArticleCreateInput!) {
  articleCreate(article: $article) {
    article { id title handle isPublished publishedAt blog { id title handle } image { altText originalSrc } }
    userErrors { code field message }
  }
}
"""
            if live:
                with live_publish_lock(store):
                    daily_protection = enforce_daily_publish_limit(store, token, version)
                    existing = graphql(store, token, version, duplicate_query, {"query": f"handle:{handle}"}).get("articles", {}).get("nodes", [])
                    if existing:
                        raise RuntimeError(f"Article handle already exists; create aborted: {json.dumps(existing, ensure_ascii=False)}")
                    mutation_result = graphql(
                        store,
                        token,
                        version,
                        mutation,
                        {"article": article},
                        retry_throttled=False,
                    ).get("articleCreate", {})
            else:
                mutation_result = graphql(
                    store,
                    token,
                    version,
                    mutation,
                    {"article": article},
                    retry_throttled=False,
                ).get("articleCreate", {})
            if mutation_result.get("userErrors"):
                raise RuntimeError(f"Shopify rejected article: {json.dumps(mutation_result['userErrors'], ensure_ascii=False)}")
            record = mutation_result.get("article")
            if not record:
                raise RuntimeError("Shopify returned no article record")
        public_url = f"https://{target}/blogs/{record['blog']['handle']}/{record['handle']}"
        result = {
            "status": "UPDATED" if update else ("PUBLISHED" if live else "SAVED_AS_DRAFT"),
            "completedAt": datetime.now(timezone.utc).isoformat(),
            "store": identity["shop"],
            "article": record,
            "publicUrl": public_url,
            "contentSha256": digest,
            "contentTier": payload.get("contentTier"),
            "publicationAction": publication_action,
            "imageAssets": uploaded.get("assets", {}),
            "organization": organization,
            "dailyPublishProtection": (
                {"applies": False, "reason": "Existing-article updates do not create a new live article."}
                if update else {
                    **(daily_protection or {"limit": configured_daily_publish_limit()}),
                    "publishedCountAfter": (daily_protection["publishedCount"] + 1) if live and daily_protection else None,
                }
            ),
        }
        if update:
            result["updateProtection"] = {
                "articleId": str(update_target["articleId"]),
                "expectedRemoteFingerprint": expected_remote_fingerprint,
                "updatedRemoteFingerprint": updated_remote_fingerprint,
                "handlePreserved": str(record.get("handle", "")) == handle,
                "blindRetry": False,
            }
        atomic_json(bundle / "publish-result.json", result)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

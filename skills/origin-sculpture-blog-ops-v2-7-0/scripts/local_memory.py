#!/usr/bin/env python3
"""Maintain persistent, local-only ORS operator and image-use memory.

The memory directory is deliberately outside the installed Skill so upgrades do
not erase it. This script never contacts Shopify or the public internet.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit


LEDGER_VERSION = 1
FEEDBACK_VERSION = 1
IMAGE_LEDGER_NAME = "image-usage-ledger.json"
FEEDBACK_INDEX_NAME = "operator-feedback-index.json"
DISCOVERY_STATE_NAME = "history-root-discovery.json"
MEMORY_ENV = "ORIGIN_BLOG_MEMORY_DIR"
HISTORY_ROOTS_ENV = "ORIGIN_BLOG_HISTORY_ROOTS"
DISCOVERY_ROOTS_ENV = "ORIGIN_BLOG_DISCOVERY_ROOTS"
AUTO_DISCOVER_ENV = "ORIGIN_BLOG_AUTO_DISCOVER"
NEAR_DUPLICATE_DISTANCE = 5
MAX_SCANNED_MANIFESTS = 5000
MAX_DISCOVERY_DIRECTORIES = 30000
MAX_DISCOVERY_DEPTH = 8
DISCOVERY_CACHE_SECONDS = 24 * 60 * 60
DISCOVERY_SKIP_NAMES = {
    ".git", ".cache", ".gradle", ".idea", ".next", ".npm", ".pnpm-store", ".venv",
    "__pycache__", "appdata", "applications", "caches", "library", "movies", "music",
    "node_modules", "pictures", "venv",
}


class LocalMemoryError(RuntimeError):
    """Raised when persistent memory cannot be trusted or updated."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_prompt(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def normalize_source_image_url(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower()
    if not host:
        return ""
    port = f":{parsed.port}" if parsed.port else ""
    path = re.sub(r"/{2,}", "/", unquote(parsed.path))
    return urlunsplit(((parsed.scheme or "https").lower(), host + port, path, "", ""))


def default_memory_dir() -> Path:
    configured = os.environ.get(MEMORY_ENV, "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / ".config" / "origin-sculpture-blog" / "operator-memory").resolve()


def environment_history_roots() -> list[Path]:
    value = os.environ.get(HISTORY_ROOTS_ENV, "").strip()
    if not value:
        return []
    roots = []
    for raw in value.split(os.pathsep):
        if raw.strip():
            roots.append(Path(raw.strip()).expanduser().resolve())
    return roots


def auto_discovery_enabled() -> bool:
    return os.environ.get(AUTO_DISCOVER_ENV, "1").strip().lower() not in {"0", "false", "no", "off"}


def discovery_search_roots() -> list[Path]:
    configured = os.environ.get(DISCOVERY_ROOTS_ENV, "").strip()
    if configured:
        candidates = [Path(raw.strip()).expanduser() for raw in configured.split(os.pathsep) if raw.strip()]
    else:
        candidates = [Path.cwd()]
        home = Path.home()
        candidates.extend(home / name for name in ("Documents", "Desktop", "Downloads"))
        for key in ("OneDrive", "OneDriveCommercial", "OneDriveConsumer"):
            value = os.environ.get(key, "").strip()
            if value:
                candidates.append(Path(value).expanduser())
        candidates.append(home)
    unique: dict[str, Path] = {}
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if not resolved.is_dir() or resolved == Path(resolved.anchor):
            continue
        unique[str(resolved)] = resolved
    return list(unique.values())


def discover_history_roots(search_roots: list[Path]) -> tuple[list[Path], int, bool]:
    found: dict[str, Path] = {}
    visited = 0
    truncated = False
    for search_root in search_roots:
        if search_root.name.lower() == "origin-blog-runs":
            found[str(search_root.resolve())] = search_root.resolve()
            continue
        for current, directories, files in os.walk(
            search_root,
            topdown=True,
            onerror=lambda _error: None,
            followlinks=False,
        ):
            visited += 1
            if visited >= MAX_DISCOVERY_DIRECTORIES:
                truncated = True
                break
            current_path = Path(current)
            file_names = {name.lower() for name in files}
            if (
                {"meta.json", "image-assets.json"}.issubset(file_names)
                or "operator-revision-record.md" in file_names
            ):
                found[str(current_path.resolve())] = current_path.resolve()
            try:
                depth = len(current_path.relative_to(search_root).parts)
            except ValueError:
                depth = MAX_DISCOVERY_DEPTH
            if depth >= MAX_DISCOVERY_DEPTH:
                directories[:] = []
                continue
            retained = []
            for name in directories:
                if name.lower() == "origin-blog-runs":
                    path = (current_path / name).resolve()
                    found[str(path)] = path
                    continue
                if name.lower() in DISCOVERY_SKIP_NAMES:
                    continue
                retained.append(name)
            directories[:] = retained
        if truncated:
            break
    return sorted(found.values()), visited, truncated


def load_discovery_state(memory_dir: Path) -> dict:
    path = memory_dir / DISCOVERY_STATE_NAME
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def auto_discover_history_roots(memory_dir: Path | None = None, *, force: bool = False) -> list[Path]:
    if not auto_discovery_enabled():
        return []
    directory = (memory_dir or default_memory_dir()).resolve()
    state = load_discovery_state(directory)
    cached = [
        Path(value).expanduser().resolve()
        for value in state.get("roots", [])
        if isinstance(value, str) and Path(value).expanduser().exists()
    ]
    try:
        last_scan = float(state.get("scannedAtEpoch", 0) or 0)
    except (TypeError, ValueError):
        last_scan = 0
    if not force and time.time() - last_scan < DISCOVERY_CACHE_SECONDS:
        return cached
    discovered, visited, truncated = discover_history_roots(discovery_search_roots())
    roots = {str(path): path for path in [*cached, *discovered] if path.is_dir()}
    atomic_json(
        directory / DISCOVERY_STATE_NAME,
        {
            "schemaVersion": 1,
            "scannedAt": utc_now(),
            "scannedAtEpoch": time.time(),
            "roots": sorted(roots),
            "directoriesVisited": visited,
            "truncated": truncated,
        },
    )
    return list(roots.values())


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def empty_ledger() -> dict:
    return {"schemaVersion": LEDGER_VERSION, "updatedAt": None, "entries": []}


def empty_feedback_index() -> dict:
    return {"schemaVersion": FEEDBACK_VERSION, "updatedAt": None, "records": []}


def load_json_index(path: Path, *, kind: str, version: int, list_key: str) -> dict:
    if not path.exists():
        return empty_ledger() if kind == "image ledger" else empty_feedback_index()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise LocalMemoryError(f"could not read {kind} {path}: {exc}") from exc
    if not isinstance(value, dict) or value.get("schemaVersion") != version:
        raise LocalMemoryError(f"unsupported or malformed {kind}: {path}")
    if not isinstance(value.get(list_key), list):
        raise LocalMemoryError(f"{kind} is missing its {list_key} array: {path}")
    return value


def load_image_ledger(memory_dir: Path | None = None) -> dict:
    directory = (memory_dir or default_memory_dir()).resolve()
    return load_json_index(
        directory / IMAGE_LEDGER_NAME,
        kind="image ledger",
        version=LEDGER_VERSION,
        list_key="entries",
    )


def load_feedback_index(memory_dir: Path | None = None) -> dict:
    directory = (memory_dir or default_memory_dir()).resolve()
    return load_json_index(
        directory / FEEDBACK_INDEX_NAME,
        kind="operator feedback index",
        version=FEEDBACK_VERSION,
        list_key="records",
    )


def safe_asset_path(bundle: Path, relative: str) -> Path | None:
    if not relative:
        return None
    root = bundle.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise LocalMemoryError(f"image path escapes its bundle: {relative}") from exc
    return candidate


def difference_hash(path: Path) -> str:
    try:
        from PIL import Image
    except ImportError as exc:
        raise LocalMemoryError("Pillow is required for local image-history checks") from exc
    with Image.open(path) as image:
        image = image.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
        pixels = list(image.getdata())
    value = 0
    for y in range(8):
        row = y * 9
        for x in range(8):
            value = (value << 1) | int(pixels[row + x] > pixels[row + x + 1])
    return f"{value:016x}"


def hash_distance(first: str, second: str) -> int | None:
    if not re.fullmatch(r"[0-9a-f]{16}", first or "") or not re.fullmatch(r"[0-9a-f]{16}", second or ""):
        return None
    return (int(first, 16) ^ int(second, 16)).bit_count()


def entry_from_asset(
    bundle: Path,
    handle: str,
    item: dict,
    *,
    recorded_at: str | None = None,
    status: str = "discovered",
) -> dict:
    png_path = safe_asset_path(bundle, str(item.get("png", "")).strip())
    webp_path = safe_asset_path(bundle, str(item.get("webp", "")).strip())
    image_path = png_path if png_path and png_path.is_file() else webp_path
    prompt = str(item.get("generationPrompt", "")).strip()
    normalized_prompt = normalize_prompt(prompt)
    source_image_url = str(item.get("sourceImageUrl", "")).strip()
    return {
        "handle": handle,
        "slot": str(item.get("slot", "")).strip(),
        "sourceType": str(item.get("sourceType", "")).strip().lower(),
        "visualRole": str(item.get("visualRole", "")).strip().lower(),
        "visualConcept": str(item.get("visualConcept", "")).strip(),
        "generationPrompt": prompt,
        "generationPromptSha256": sha256_text(normalized_prompt) if normalized_prompt else "",
        "sourcePage": str(item.get("sourcePage", "")).strip(),
        "sourceImageUrl": source_image_url,
        "sourceImageKey": normalize_source_image_url(source_image_url),
        "pngPath": str(png_path) if png_path and png_path.is_file() else "",
        "webpPath": str(webp_path) if webp_path and webp_path.is_file() else "",
        "pngSha256": sha256_file(png_path) if png_path and png_path.is_file() else "",
        "webpSha256": sha256_file(webp_path) if webp_path and webp_path.is_file() else "",
        "differenceHash": difference_hash(image_path) if image_path and image_path.is_file() else "",
        "reuseApproved": item.get("reuseApproved") is True,
        "reuseReason": str(item.get("reuseReason", "")).strip(),
        "bundlePath": str(bundle.resolve()),
        "recordedAt": recorded_at or utc_now(),
        "status": status,
    }


def entries_from_bundle(bundle: Path, *, status: str = "discovered") -> list[dict]:
    bundle = bundle.resolve()
    meta_path = bundle / "meta.json"
    manifest_path = bundle / "image-assets.json"
    if not meta_path.is_file() or not manifest_path.is_file():
        return []
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise LocalMemoryError(f"could not parse image history bundle {bundle}: {exc}") from exc
    handle = str(meta.get("handle", "")).strip()
    if not handle or not isinstance(manifest, list):
        return []
    entries = []
    for item in manifest:
        if isinstance(item, dict) and str(item.get("slot", "")).strip():
            entries.append(entry_from_asset(bundle, handle, item, status=status))
    return entries


def entry_identity(entry: dict) -> tuple[str, ...]:
    visual_identity = (
        str(entry.get("pngSha256", ""))
        or str(entry.get("webpSha256", ""))
        or str(entry.get("sourceImageKey", ""))
        or str(entry.get("generationPromptSha256", ""))
        or str(entry.get("bundlePath", ""))
    )
    return (
        str(entry.get("handle", "")),
        str(entry.get("slot", "")),
        visual_identity,
    )


def merge_entries(existing: list[dict], incoming: list[dict]) -> list[dict]:
    merged: dict[tuple[str, ...], dict] = {}
    for entry in [*existing, *incoming]:
        if not isinstance(entry, dict):
            continue
        identity = entry_identity(entry)
        if not all(identity):
            continue
        previous = merged.get(identity)
        if previous and str(previous.get("recordedAt", "")) > str(entry.get("recordedAt", "")):
            continue
        merged[identity] = entry
    return sorted(
        merged.values(),
        key=lambda item: (
            str(item.get("recordedAt", "")),
            str(item.get("handle", "")),
            str(item.get("slot", "")),
        ),
    )


def markdown_section(text: str, aliases: tuple[str, ...]) -> str:
    headings = list(re.finditer(r"(?m)^#{1,6}\s+(.+?)\s*$", text))
    lowered_aliases = tuple(alias.lower() for alias in aliases)
    for index, heading in enumerate(headings):
        title = re.sub(r"^[0-9]+[.)、]?\s*", "", heading.group(1).replace("**", "").strip()).lower()
        if not any(alias in title for alias in lowered_aliases):
            continue
        start = heading.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        return text[start:end].strip()
    return ""


def feedback_record(path: Path) -> dict:
    bundle = path.parent.resolve()
    handle = bundle.name
    meta_path = bundle / "meta.json"
    if meta_path.is_file():
        try:
            handle = str(json.loads(meta_path.read_text(encoding="utf-8")).get("handle", handle)).strip() or handle
        except Exception:
            pass
    text = path.read_text(encoding="utf-8", errors="replace")
    sections = {
        "limitedReusableSignals": markdown_section(
            text, ("limited reusable signals", "有限可复用", "可有限复用")
        ),
        "localOnlyChanges": markdown_section(
            text, ("local-only changes", "local only changes", "仅限当前文章", "局部修改")
        ),
        "prohibitedInferences": markdown_section(
            text, ("prohibited inferences", "禁止推导", "禁止推断")
        ),
        "pendingOperatorQuestions": markdown_section(
            text, ("pending operator questions", "待运营确认", "待确认问题")
        ),
        "promotionDecision": markdown_section(
            text, ("promotion decision", "推广决定", "规则升级决定")
        ),
    }
    promotion = "unclassified"
    decision_text = sections["promotionDecision"]
    if decision_text:
        lowered = decision_text.lower()
        if "promote with explicit user approval" in lowered or "明确批准" in decision_text:
            promotion = "promote-with-explicit-user-approval"
        elif "propose promotion" in lowered or "建议升级" in decision_text:
            promotion = "propose-promotion"
        elif "record only" in lowered or "仅记录" in decision_text:
            promotion = "record-only"
    return {
        "handle": handle,
        "path": str(path.resolve()),
        "sha256": sha256_file(path),
        "modifiedAt": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
        "promotionDecision": promotion,
        "sections": sections,
    }


def discover_files(roots: list[Path], filename: str) -> list[Path]:
    discovered: dict[str, Path] = {}
    for root in roots:
        root = root.expanduser().resolve()
        if not root.exists():
            continue
        candidates = [root] if root.is_file() and root.name == filename else []
        if root.is_dir():
            direct = root / filename
            if direct.is_file():
                candidates.append(direct)
            candidates.extend(root.rglob(filename))
        for path in candidates:
            discovered[str(path.resolve())] = path.resolve()
            if len(discovered) > MAX_SCANNED_MANIFESTS:
                raise LocalMemoryError(
                    f"history scan exceeded {MAX_SCANNED_MANIFESTS} {filename} files; use a narrower runs root"
                )
    return sorted(discovered.values())


def bootstrap_memory(
    roots: list[Path],
    *,
    memory_dir: Path | None = None,
    exclude_bundle: Path | None = None,
) -> dict:
    directory = (memory_dir or default_memory_dir()).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    excluded = exclude_bundle.resolve() if exclude_bundle else None

    ledger = load_image_ledger(directory)
    incoming: list[dict] = []
    skipped: list[str] = []
    manifests = discover_files(roots, "image-assets.json")
    for manifest in manifests:
        bundle = manifest.parent.resolve()
        if excluded and bundle == excluded:
            continue
        try:
            incoming.extend(entries_from_bundle(bundle))
        except LocalMemoryError as exc:
            skipped.append(str(exc))
    ledger["entries"] = merge_entries(ledger["entries"], incoming)
    ledger["updatedAt"] = utc_now()
    atomic_json(directory / IMAGE_LEDGER_NAME, ledger)

    feedback = load_feedback_index(directory)
    records = [feedback_record(path) for path in discover_files(roots, "operator-revision-record.md")]
    record_map = {
        str(item.get("path", "")): item
        for item in [*feedback["records"], *records]
        if isinstance(item, dict) and item.get("path")
    }
    feedback["records"] = sorted(record_map.values(), key=lambda item: str(item.get("modifiedAt", "")))
    feedback["updatedAt"] = utc_now()
    atomic_json(directory / FEEDBACK_INDEX_NAME, feedback)
    return {
        "memoryDir": str(directory),
        "roots": [str(path.resolve()) for path in roots],
        "manifestsScanned": len(manifests),
        "imageEntries": len(ledger["entries"]),
        "feedbackRecords": len(feedback["records"]),
        "skipped": skipped,
    }


def exact_match(current: dict, prior: dict) -> bool:
    current_hashes = {
        value for value in (current.get("pngSha256"), current.get("webpSha256")) if value
    }
    prior_hashes = {value for value in (prior.get("pngSha256"), prior.get("webpSha256")) if value}
    return bool(current_hashes & prior_hashes)


def source_match(current: dict, prior: dict) -> bool:
    return bool(
        current.get("sourceImageKey")
        and current.get("sourceImageKey") == prior.get("sourceImageKey")
    )


def prompt_match(current: dict, prior: dict) -> bool:
    return bool(
        current.get("generationPromptSha256")
        and current.get("generationPromptSha256") == prior.get("generationPromptSha256")
    )


def audit_entries(handle: str, current: list[dict], history: list[dict]) -> dict:
    blockers: list[str] = []
    warnings: list[str] = []
    matches: list[dict] = []
    for index, candidate in enumerate(current):
        for prior in current[:index]:
            if not any((exact_match(candidate, prior), source_match(candidate, prior), prompt_match(candidate, prior))):
                continue
            blockers.append(
                f"image asset '{candidate.get('slot')}' duplicates asset '{prior.get('slot')}' "
                "inside the current article bundle"
            )
    for candidate in current:
        slot = str(candidate.get("slot", ""))
        source_type = str(candidate.get("sourceType", ""))
        for prior in history:
            prior_handle = str(prior.get("handle", ""))
            if not prior_handle or prior_handle == handle:
                continue
            is_exact = exact_match(candidate, prior)
            is_source = source_match(candidate, prior)
            is_prompt = prompt_match(candidate, prior)
            distance = hash_distance(
                str(candidate.get("differenceHash", "")),
                str(prior.get("differenceHash", "")),
            )
            is_near = distance is not None and distance <= NEAR_DUPLICATE_DISTANCE
            if not any((is_exact, is_source, is_prompt, is_near)):
                continue
            match = {
                "slot": slot,
                "sourceType": source_type,
                "priorHandle": prior_handle,
                "priorSlot": prior.get("slot"),
                "exactBytes": is_exact,
                "sameSourceImage": is_source,
                "sameGenerationPrompt": is_prompt,
                "differenceHashDistance": distance,
                "priorBundlePath": prior.get("bundlePath"),
            }
            matches.append(match)
            if source_type == "generated-editorial":
                reason = (
                    "uses the same image bytes" if is_exact else
                    "uses a previously used generation prompt" if is_prompt else
                    f"visually matches a prior image (difference-hash distance {distance})"
                )
                blockers.append(
                    f"generated image asset '{slot}' {reason} from article '{prior_handle}'; "
                    "generate a genuinely new visual for this article"
                )
                continue
            reuse_reason = str(candidate.get("reuseReason", "")).strip()
            if candidate.get("reuseApproved") is not True or len(reuse_reason) < 12:
                blockers.append(
                    f"image asset '{slot}' reuses media from article '{prior_handle}'; "
                    "choose another image or set reuseApproved true with a specific reuseReason"
                )
            else:
                warnings.append(
                    f"image asset '{slot}' reuses media from article '{prior_handle}' with an explicit reason"
                )
    return {
        "status": "PASS" if not blockers else "BLOCKED",
        "ledgerEntriesCompared": len(history),
        "nearDuplicateDistance": NEAR_DUPLICATE_DISTANCE,
        "sameHandleRevisionReuseAllowed": True,
        "matches": matches,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }


def audit_bundle(
    bundle: Path,
    *,
    handle: str,
    assets: list[dict],
    memory_dir: Path | None = None,
) -> tuple[dict, list[dict]]:
    directory = (memory_dir or default_memory_dir()).resolve()
    current = [entry_from_asset(bundle, handle, item, status="candidate") for item in assets]
    history = load_image_ledger(directory)["entries"]
    report = audit_entries(handle, current, history)
    report["memoryDir"] = str(directory)
    report["ledgerPath"] = str(directory / IMAGE_LEDGER_NAME)
    return report, current


def record_prepared_entries(entries: list[dict], *, memory_dir: Path | None = None) -> dict:
    directory = (memory_dir or default_memory_dir()).resolve()
    ledger = load_image_ledger(directory)
    now = utc_now()
    prepared = []
    for entry in entries:
        copy = dict(entry)
        copy["status"] = "prepared"
        copy["recordedAt"] = now
        prepared.append(copy)
    ledger["entries"] = merge_entries(ledger["entries"], prepared)
    ledger["updatedAt"] = now
    atomic_json(directory / IMAGE_LEDGER_NAME, ledger)
    return {
        "ledgerPath": str(directory / IMAGE_LEDGER_NAME),
        "recorded": len(prepared),
        "total": len(ledger["entries"]),
    }


def roots_for_bundle(bundle: Path) -> list[Path]:
    roots = [
        bundle.resolve().parent,
        *environment_history_roots(),
        *auto_discover_history_roots(default_memory_dir()),
    ]
    unique: dict[str, Path] = {str(path): path for path in roots}
    return list(unique.values())


def context_payload(handle: str, memory_dir: Path, limit: int) -> dict:
    ledger = load_image_ledger(memory_dir)
    feedback = load_feedback_index(memory_dir)
    images = [
        {
            key: entry.get(key)
            for key in (
                "handle", "slot", "sourceType", "visualRole", "visualConcept",
                "generationPrompt", "sourcePage", "sourceImageUrl", "pngPath", "webpPath",
                "bundlePath", "recordedAt",
            )
        }
        for entry in ledger["entries"]
        if str(entry.get("handle", "")) != handle
    ]
    images = images[-limit:]
    records = feedback["records"][-limit:]
    return {
        "memoryDir": str(memory_dir),
        "currentHandle": handle,
        "instruction": (
            "Read topic-relevant operator records before drafting. Treat record-only/local-only content as bounded "
            "evidence, not a global rule. Do not reuse an image or exact generation prompt listed under priorImages."
        ),
        "priorImages": images,
        "operatorRevisionRecords": records,
    }


def command_roots(raw_roots: list[Path], memory_dir: Path) -> list[Path]:
    roots = [path.expanduser().resolve() for path in raw_roots]
    roots.extend(environment_history_roots())
    roots.extend(auto_discover_history_roots(memory_dir))
    default = (Path.cwd() / "origin-blog-runs").resolve()
    if default.exists():
        roots.append(default)
    unique = {str(path): path for path in roots}
    return list(unique.values())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory-dir", type=Path, help=f"Override {MEMORY_ENV} for this command")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap = subparsers.add_parser("bootstrap", help="Index prior image manifests and operator revision records")
    bootstrap.add_argument("--runs-root", type=Path, action="append", default=[])

    status = subparsers.add_parser("status", help="Show local memory counts without scanning")
    status.add_argument("--verbose", action="store_true")

    context = subparsers.add_parser("context", help="Bootstrap and print pre-draft local context")
    context.add_argument("--handle", required=True)
    context.add_argument("--runs-root", type=Path, action="append", default=[])
    context.add_argument("--limit", type=int, default=200)

    args = parser.parse_args()
    memory_dir = (args.memory_dir.expanduser().resolve() if args.memory_dir else default_memory_dir())
    try:
        if args.command == "bootstrap":
            roots = command_roots(args.runs_root, memory_dir)
            result = bootstrap_memory(roots, memory_dir=memory_dir)
        elif args.command == "context":
            roots = command_roots(args.runs_root, memory_dir)
            bootstrap_result = bootstrap_memory(roots, memory_dir=memory_dir)
            result = context_payload(args.handle, memory_dir, max(1, args.limit))
            result["bootstrap"] = bootstrap_result
        else:
            ledger = load_image_ledger(memory_dir)
            feedback = load_feedback_index(memory_dir)
            handles = sorted({str(item.get("handle", "")) for item in ledger["entries"] if item.get("handle")})
            result = {
                "memoryDir": str(memory_dir),
                "imageLedger": str(memory_dir / IMAGE_LEDGER_NAME),
                "feedbackIndex": str(memory_dir / FEEDBACK_INDEX_NAME),
                "imageEntries": len(ledger["entries"]),
                "articleHandles": len(handles),
                "feedbackRecords": len(feedback["records"]),
                "autoDiscovery": load_discovery_state(memory_dir),
            }
            if args.verbose:
                result["handles"] = handles
                result["operatorRevisionRecords"] = feedback["records"]
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, indent=2, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

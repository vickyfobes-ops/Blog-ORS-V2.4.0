# Local operator learning and image memory

Use this contract for every ORS article. It makes operator learning persistent without rewriting the installed Skill after every article and prevents prior article imagery from silently becoming the default for new work.

## Storage boundary

The installed Skill contains the stable method and the merchant-approved rules. The operator computer contains its evolving evidence and image history. By default, the local memory lives at:

```text
~/.config/origin-sculpture-blog/operator-memory/
```

Set `ORIGIN_BLOG_MEMORY_DIR` only when the operator intentionally wants another persistent location. Never store this directory inside the versioned Skill folder; reinstalling or upgrading a Skill must not erase local history.

The memory contains:

- `image-usage-ledger.json`: image hashes, visual fingerprints, generation prompts, source media, article handles, and bundle paths;
- `operator-feedback-index.json`: paths and fingerprints of local `operator-revision-record.md` files.

These files contain no Shopify credential and the memory tool never calls Shopify or the internet.

## Required pre-draft read

After establishing the intended handle and before outlining, selecting site images, or generating new images, run:

```bash
python scripts/local_memory.py context \
  --handle <current-handle> \
  --runs-root <working-directory>/origin-blog-runs
```

The command first indexes previously saved run bundles and operator revision records, then returns local context. Read topic-relevant records listed under `operatorRevisionRecords`. Apply only their `Limited reusable signals` within the recorded conditions. Preserve `Local-only changes`, `Prohibited inferences`, unanswered questions, and `record only` decisions as boundaries. A local record never overrides the release lock, evidence requirements, Shopify approval, or the maintained rules in `operator-editing-rules.md`.

Use `priorImages` as a negative selection list. Do not select, copy, regenerate from the exact same prompt, or present a prior generated visual as a new article asset. A repeated subject such as “studio inspection” is allowed only when the composition, setting, decision purpose, and resulting visual are genuinely new.

## Bootstrap after installation

On the operator computer, index every known historical `origin-blog-runs` root once:

```bash
python scripts/local_memory.py bootstrap \
  --runs-root <absolute-path-to-origin-blog-runs>

python scripts/local_memory.py status --verbose
```

Repeat `--runs-root` for additional locations. On future runs, `context` and `prepare_bundle.py` automatically merge the active run root. If historical bundles were deleted, the Skill cannot reconstruct their image bytes; disclose that the ledger protects only history still available at bootstrap plus all future prepared bundles.

For multiple persistent roots, `ORIGIN_BLOG_HISTORY_ROOTS` may contain absolute paths separated by the operating system path separator (`;` on Windows, `:` on macOS/Linux).

## Image reuse policy

- A revision using the same article handle may retain its approved images by default.
- Across different handles, an exact or perceptually near-duplicate `generated-editorial` image is a hard blocker. An exact reused generation prompt is also a blocker even if the renderer returns slightly different pixels.
- Across different handles, an Origin-owned or user-provided image may be reused only when it remains the strongest direct evidence. Set `reuseApproved: true` and write a specific `reuseReason` in `image-assets.json`; otherwise preparation blocks.
- Reuse approval never permits a generated editorial image to be recycled across articles.
- `prepare_bundle.py` compares SHA-256 bytes, normalized source-media URLs, and a deterministic visual difference hash. It writes a passing bundle into local history before issuing an approval phrase.
- Missing, corrupt, or unwritable memory is a preparation blocker. Do not bypass it by deleting the ledger or changing the memory directory for one article.

Every new `generated-editorial` manifest entry must preserve:

```json
{
  "visualConcept": "topic-specific visual purpose and composition",
  "generationPrompt": "the complete prompt actually used to generate this image"
}
```

These fields are operational provenance, not public copy.

## Record operator changes without over-learning

After creating or updating `<run-dir>/operator-revision-record.md`, rerun `local_memory.py bootstrap` for that run root. Future tasks can then find the record from the persistent index.

Do not edit `SKILL.md` automatically from an operator revision. Stable promotion still requires explicit user approval or repeated approved evidence under `operator-revision-review.md`. This separation lets the operator computer learn continuously while preventing a one-off wording change, service claim, image choice, or article structure from becoming a site-wide rule.

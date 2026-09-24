---
name: origin-sculpture-blog-ops-v2-7-0
description: Latest default Origin Sculpture Blog workflow; use this version instead of every earlier origin-sculpture-blog variant whenever the user supplies any ORS blog topic, even if they provide only the topic and do not name a skill. Create, review, revise, validate, publish, and safely update source-backed American English Shopify articles. Automatically discover and read persistent local operator/image history, block generated-image reuse across articles, and audit operator edits without turning one-off changes into global rules. Also use for outlines, revised Markdown/HTML/DOCX, internal links, pre-publish QA, existing-article revisions, operator-change reviews, or exact approved create/update actions. Trigger on Origin Sculpture blog, ORS blog, 雕塑博客自动化、写博客、审核文章、修改原文章、添加内链、上传博客、发布 Shopify 文章, or explicit $origin-sculpture-blog-ops-v2-7-0 invocation.
metadata:
  version: "2.7.0"
---

# Origin Sculpture Blog

Turn one topic or existing Origin article into an approval-ready, internally linked article and mutate Shopify only with the exact action-specific approval. Default planning and review notes to Chinese and the public article to American English.

## Load the required standards

- Read [references/release-lock-v2.4.5.md](references/release-lock-v2.4.5.md) first for every request. It is the release-level, fail-closed contract for the latest merchant-approved live/article and Word format.
- Read [references/workflow-contract.md](references/workflow-contract.md) for every request.
- Read [references/local-learning-memory.md](references/local-learning-memory.md) for every request. Its local record read and image-history check are required, not optional cleanup.
- Read [references/origin-brand-and-site.md](references/origin-brand-and-site.md) before research, drafting, linking, or publication.
- Read [references/editorial-seo-geo.md](references/editorial-seo-geo.md) before outlining or drafting.
- Read [references/quality-gate.md](references/quality-gate.md) before delivering a review draft or preparing publication.
- Read [references/operator-editing-rules.md](references/operator-editing-rules.md) when revising an existing article, reviewing operator changes, or drafting custom-process, installation-coordination, material, finish, or delivery content.
- Read [references/operator-revision-review.md](references/operator-revision-review.md) whenever an operator has changed a prior draft, Word file, Shopify draft, or live article and the user asks to learn from those changes.
- Read [references/benchmark-analysis.md](references/benchmark-analysis.md) when choosing a structure, explaining the recommended model, or comparing examples.
- Read [references/word-output.md](references/word-output.md) whenever creating or checking the Word review artifact.
- Read [references/shopify-setup.md](references/shopify-setup.md) only for setup, credential checks, dry runs, or publication.

## Follow the three-step workflow

### 1. Accept the topic and build evidence

Treat one usable topic as sufficient input. Infer the target reader, setting, funnel stage, primary query, and article model. Ask only when a missing business fact would materially alter the article.

Establish the intended handle, then load the operator computer's persistent context before outlining, choosing Origin media, or generating imagery:

```bash
python scripts/local_memory.py context \
  --handle <current-handle>
```

This command automatically searches the current workspace and the operator's common local work locations for existing `origin-blog-runs`, remembers every discovered root, and incrementally indexes it. Do not ask the operator to locate folders or run a bootstrap command before accepting a topic. Read topic-relevant `operatorRevisionRecords` returned by the command and preserve their recorded scope. Use `priorImages` as a negative selection list; compare their concepts/prompts and inspect the returned local PNG paths for generated images with a matching role or subject before generating a new visual. If the local memory cannot be read or updated, repair it within the task or report the concrete runtime error; do not turn normal setup into a user prerequisite.

Classify the topic twice before outlining. First choose `pillar` for a broad cluster hub at 1,800–2,500 useful body words or `supporting` for one narrow reader task at 1,000–1,600. Second choose `site-led` for ordering, custom process, company/service, and how-to-work-with-us topics, or `expert-led` for materials, finishes, trends, inspiration, maintenance, installation, and site-planning topics. Record both as `contentTier` and `editorialMode` in `meta.json`. Do not broaden a supporting topic merely to reach length. Record one primary query and three to eight natural supporting or long-tail queries; use them only where they help the reader.

Browse for current, technical, regional, safety, pricing, named-project, or otherwise verifiable claims. Prefer standards bodies, government agencies, museums, technical associations, and original project sources. Never invent material grades, finishes, prices, lead times, warranties, certifications, clients, projects, or service scope. Mark missing business facts as `[BUSINESS INPUT NEEDED: ...]`; do not prepare a publish token while any marker remains.

Refresh the link inventory before choosing links:

```bash
python scripts/site_inventory.py crawl \
  --site https://originsculpture.com \
  --output <run-dir>/site-inventory.json

python scripts/site_inventory.py search \
  --inventory <run-dir>/site-inventory.json \
  --query "<topic and intent terms>" \
  --kind product \
  --limit 12
```

Use only canonical URLs returned by the live sitemap. Select links for reader utility and semantic fit, never merely to meet a count.

### 2. Deliver one review package

Create `<working-directory>/origin-blog-runs/<handle>/` containing:

- `brief.md`: audience, intent, primary query, content model/tier, editorial mode, promise, approved Origin experience evidence, evidence gaps, and recommended structure;
- `article.md`: readable review version with the SEO pack and full article;
- `article.html`: Shopify body-only HTML without an H1; `meta.json.title` is the intended page H1, subject to the selected live theme/template check below;
- `summary.html`: concise excerpt;
- `meta.json`: publication metadata following the schema in `workflow-contract.md`;
- `link-plan.json`: every contextual internal link and its relevance reason;
- `sources.md`: authoritative sources with retrieval dates and claim mapping;
- `image-plan.md`: cover and inline-image briefs plus descriptive alt text;
- `image-assets.json`, `images/*.png`, and `images/*.webp`: the approved cover and inline images, with stable slots, exact heading placements, and alt text;
- `site-inventory.json`: current canonical URL inventory.

Use at least five contextual Origin Sculpture links in the article body, including at least three distinct, relevant `/products/` URLs and normally at least two related `/blogs/` URLs. Distribute them across the sections where they answer the next reader question; do not cluster them into one paragraph, repeat one anchor formula, or insert a product merely to meet the count. A navigation link, footer link, raw URL list, or generic “click here” does not count. Do not guess a product URL.

Write a clear public title in `meta.json.title` aligned with the reader's main question or decision. The review Markdown and Word document may show that title, but never paste their H1 into `article.html`. Start the body with a standalone answer paragraph before the first H2; about 40–70 English words is a useful editorial target, not a keyword/length gate. Use H2s for distinct reader questions or decisions and H3s only beneath the relevant H2. Do not copy a WordPress-specific outer class or its page typography into the Shopify body. Keep ordinary visual styling in the Shopify theme; use an inline-styled callout only when its treatment is actually supported and reviewed in the selected template.

Assign one focused `blogFilters` value from the store-approved list in `workflow-contract.md`. Base it on the article's dominant reader task, not incidental material mentions. `prepare_bundle.py` infers a conservative primary value for a legacy bundle that omits the field, but new bundles should record the choice explicitly. Use `templateSuffix: null` unless the merchant has confirmed an alternate article template exists in the live theme and configured its suffix during setup.

Include one topic-specific Origin Sculpture experience section totaling about 10–20% of the public body words. Give it a heading that describes the actual decision or control point; never use a repeated `Why Choose Origin` heading. Use only verified Origin practice relevant to the topic, such as material selection, finish approval, a physical/control sample, production sequence, QC/inspection, installation environment, packing, or maintenance checks. Connect at least two relevant experience signals, but do not force every signal into every article. Do not invent projects, measurements, client preferences, factory statistics, or outcomes.

Wrap this visible section in non-rendering publication markers:

```html
<!-- origin-experience:start -->
<h2>How a Physical Finish Sample Prevents Production Rework</h2>
...
<!-- origin-experience:end -->
```

Record the supporting live Origin page or user-provided evidence under `## Origin experience evidence` in `sources.md`. If no evidence supports a desired first-hand claim, remove the claim or mark the business input as unresolved; never convert general industry advice into claimed Origin experience.

Use six to eight useful images including the cover. Every article must include two or three directly relevant Origin-owned product/project images selected from current Origin pages; each source page must also appear naturally as a contextual internal link. Download the original media file, never a webpage screenshot, and record both `sourcePage` and `sourceImageUrl`. AI-generated photorealistic environment, material, and process scenes remain the primary visual system: at least 60% of the image manifest and normally the cover. Before generating, compare the plan against local `priorImages`; create a genuinely new composition and save the complete actual `generationPrompt` plus a specific `visualConcept` in each generated manifest entry. Never copy, reselect, or regenerate from an exact prompt already used by another article. Do not use a laptop, phone, webpage, storefront UI, gallery grid, visible logo, watermark, or generated text as the main visual. Never present a generated scene as a completed Origin project. Normalize every approved source into the locked 1600×900 pair before bundling:

```bash
python scripts/normalize_image_asset.py <downloaded-original> \
  --output-dir <run-dir>/images \
  --slot <stable-slot> \
  --focal-x 0.5 --focal-y 0.5
```

The PNG is for Word and the WebP is for Shopify. Adjust the focal point only after opening the image and confirming the sculpture is not cropped incorrectly. If the normalizer reports `upscaled: true`, inspect the 1600×900 output at full size and choose a sharper Origin image when the result looks soft or artifacted. Visually inspect every approved output, then record `sourceType`, `visualRole`, and all four true `visualQa` results defined in `workflow-contract.md`; a missing or false check blocks preparation. Across different handles, `prepare_bundle.py` blocks exact or perceptually near-duplicate generated images. A same-handle revision may retain its media. Reusing an Origin-owned/user-provided image across handles requires `reuseApproved: true` and a concrete `reuseReason`. Use `origin-asset://<slot>` in `article.html`, never publish a local path, and distribute images and internal links by reader need rather than clustering them.

Run the gate and generate the approval-bound payload:

```bash
python scripts/prepare_bundle.py <run-dir> \
  --inventory <run-dir>/site-inventory.json \
  --check-links
```

Fix all blockers. Deliver the article for review, summarize material caveats, list the chosen product links and why each belongs, and show the exact live and draft confirmation phrases from `approval.json`. End in `AWAITING_APPROVAL`. Do not publish in the same turn that first presents a new or materially revised article.

Also generate the clean final-upload Word review document defined in `references/word-output.md`. It must use black visible text, follow the Origin site hierarchy, include the approved images in their declared positions, and omit editorial/review chrome:

```bash
python scripts/build_publish_docx.py \
  <run-dir> \
  <run-dir>/<Title>-Final-Upload.docx

python scripts/verify_publish_docx.py \
  <run-dir>/<Title>-Final-Upload.docx \
  --bundle <run-dir>
```

First resolve and use the document-capable Python runtime supplied by the Codex workspace dependencies; do not fall back to system Python or improvise a replacement generator. `build_publish_docx.py` is the only allowed DOCX generator for this workflow. Never hand-build or redesign the DOCX with Word defaults, a generic document preset, a fresh webpage interpretation, or an ad hoc script. If the builder, bundled fonts, verifier, or renderer is unavailable, report the dependency as a blocker and stop the Word deliverable instead of changing the format.

The builder must use the Origin custom styles and pass `verify_publish_docx.py`. Render every page to PNG and inspect it against `assets/format-reference/latest-format-page-1.png`; reject blue/theme-colored text, serif body copy, missing Poppins or Libre Baskerville embedding, sans-serif heading fallback, wrong first-page order, headers/footers, or any visible style outside the approved Origin style set. Do not show an approval phrase or `AWAITING_APPROVAL` until both structural verification and visual QA pass.

Present the DOCX as the primary review artifact; keep SEO notes, source ledgers, caveats, approval phrases, and internal production metadata in the conversation or bundle, not as colored headers, footers, watermarks, or review pages inside the document.

If the user requests changes, revise the package, rerun preparation, and show the new phrases. Any edit invalidates the old hash and phrase.

When an operator has revised a prior ORS article, first compare the old and new approved bytes. Record the observed delta and its limits in [references/operator-editing-rules.md](references/operator-editing-rules.md). Do not promote a one-off operator edit into a global rule; only reuse a pattern when the topic supports it and the evidence remains valid.

For an operator-revision audit, follow [references/operator-revision-review.md](references/operator-revision-review.md). Save the evidence-bound comparison as `<run-dir>/operator-revision-record.md`. It must separate actual deltas, limited reusable signals, local-only edits, prohibited inferences, and pending operator questions. Do not change the long-lived `operator-editing-rules.md` merely because one review record exists; update it only after the user explicitly requests the promotion or the same pattern is evidenced in multiple approved revisions.

After saving that record, continue normally. The next automatic context/preparation pass indexes it on the same operator computer; do not assign a separate setup step to the operator.

For an existing Shopify article, create a separate revision bundle instead of overwriting its prior publication record. Set `publicationAction: "update"` in `meta.json`, capture the current remote target before preparation, and preserve the approved handle:

```bash
python scripts/shopify_publish.py \
  --bundle <revision-run-dir> \
  --capture-update-target
```

The resulting `update-target.json` binds the review to one Article ID and a fingerprint of the current live content. If the article changes in Shopify before execution, discard the stale approval, recapture the target, rerun preparation, and request a new phrase.

If the user supplies DOCX, use the available document-reading capability to preserve headings, links, lists, and tables; normalize it into the same bundle. Report any lossy conversion or content change, run the gate, and request approval for the normalized version.

### 3. Create or update only the approved bytes

Treat only the exact phrase in `approval.json` as authorization for the matching bundle and mode:

- `确认发布 <handle> <hash8>` creates a live article.
- `确认保存草稿 <handle> <hash8>` creates an unpublished Shopify draft.
- `确认更新 <handle> <hash8>` updates the exact captured Shopify article while preserving its handle and publication status.

General praise, “looks good,” “OK,” “确认,” or approval of an earlier hash is not publication authorization. If the user attaches a new document or changes text, return to step 2.

Immediately before publication, rerun `prepare_bundle.py` with the same inventory and link checks. Verify the target store and blog, then execute:

```bash
python scripts/shopify_publish.py \
  --bundle <run-dir> \
  --confirm "<exact phrase>"
```

The publisher refuses changed source files, wrong stores, duplicate create handles, mismatched update IDs/fingerprints, missing credentials, GraphQL user errors, and stale confirmations. Never print, store, or echo the Admin API token. After success, report the article ID, action, canonical URL, timestamp, and `publish-result.json` path. Never retry a create or update mutation blindly after an ambiguous network failure; reconcile the handle or target fingerprint first.

Before creating the article, the publisher reads the live `custom.blog_filter` definition and blocks values Shopify no longer allows. It sets the approved Blog Filter with the SEO metafields. It uses the default article template when `templateSuffix` is null. For a custom suffix, require it in the protected `SHOPIFY_ARTICLE_TEMPLATE_SUFFIXES` allowlist; never guess or silently create a theme template.

Before recommending manual publication of a draft or executing a live-publication step, confirm read-only that a public article using the same selected theme/template renders exactly one visible H1 containing its public article title. Record the checked page, template match, date, and observed H1 in the review notes; recheck after a theme/template change. A published example from another template does not establish this. If the template cannot be verified or renders zero/multiple H1s, do not claim the page has a unique H1 or publish live: flag the theme issue for a human to fix, keep `article.html` H1-free, and leave an authorized draft unpublished. This check cannot be replaced by inserting an H1 in the body.

Apply the operational safety controls in `shopify_publish.py`. Retry only explicit Shopify throttling responses, honor `Retry-After`, and use bounded exponential backoff. Never auto-retry `articleCreate` or `articleUpdate`. Before an update, compare the captured remote fingerprint twice and block if Shopify changed. For a new live publication, enforce the configured store-wide daily limit twice—before asset upload and immediately before creation under a local process lock. Count by the Shopify store timezone. Drafts and edits to an already-published article do not consume the new-article limit. Default to three new live articles per store day.

For first-time setup, read `references/shopify-setup.md`, configure the protected credential file, and run `--verify-store`. This one-time setup is outside the three recurring operator actions.

## Apply the non-negotiable rules

- Optimize for the reader's decision before keyword coverage.
- Give the direct answer or decision orientation in the opening 80 words.
- Keep one intended page title/H1 in metadata; begin the body with an answer paragraph, not an `Introduction` heading. Verify the selected template really renders that title as the sole H1 before live publication.
- Use question-led or decision-led H2s, parallel H3s, a comparison device when useful, a specification/checklist section, and concise FAQs only when they resolve real follow-up questions.
- Distinguish substrate, fabrication, surface finish, coating, environment, and maintenance. Do not imply that finish alone determines durability.
- Attribute factual claims to authoritative sources. Treat Origin Sculpture product pages as product evidence, not independent technical evidence.
- Use natural American English, concrete nouns, short paragraphs, useful transitions, and restrained brand language. Avoid luxury filler, unsupported superlatives, fake quotations, and repetitive conclusions.
- For `site-led` service/process articles, write for an ordinary buyer: anchor the article in current Origin pages and customer decisions, keep technical/process explanation to about 20–30%, define unavoidable terms immediately, and omit factory-SOP detail that does not change the customer's next action. For `expert-led` articles, professional terminology is allowed when it improves a material, trend, inspiration, maintenance, installation, or site decision, but explain each term on first use and connect it to a practical consequence.
- Keep Pillar Blogs at 1,800–2,500 useful body words and Supporting Blogs at 1,000–1,600; treat the declared `contentTier` as a hard gate.
- Keep the marked Origin experience section at 10–20% of body words, useful to the reader rather than promotional filler.
- Do not publish with placeholders, broken links, tracking parameters, preview URLs, missing alt text, or fewer than three relevant product links.
- Do not reset, relocate, or delete local memory to make a reused image pass. Missing or corrupt memory is a blocker. Same-handle revisions may retain images; different handles may not reuse generated images or exact generation prompts.

## Use the scripts as hard controls

- `scripts/self_test.py`: after every fresh install or version update, build a clean local fixture bundle, run the positive and negative gates, generate and verify a DOCX, render it, and compare the locked first-page typography/layout geometry with cross-platform raster tolerance. Raw pixel drift is diagnostic; structural violations or material layout drift still fail closed. It never contacts Shopify. Do not use the installed version for production until this command returns `PASS`.
- `scripts/local_memory.py`: automatically discover, index, and read persistent operator-revision and image-use history outside the installed Skill. It performs no network or Shopify action. Run `context` before drafting and image generation; `prepare_bundle.py` repeats discovery and records every passing image set automatically. `bootstrap` is a repair/import command, not a normal operator prerequisite.
- `scripts/normalize_image_asset.py`: convert an approved original image into the required 1600×900 sRGB PNG/WebP pair with an explicit focal point and stripped metadata.
- `scripts/site_inventory.py`: crawl the canonical sitemap and rank candidate links.
- `scripts/prepare_bundle.py`: audit structure, content-tier length, marked/evidenced Origin experience, metadata, link counts, source files, unsafe HTML, canonical inventory membership, live link status, persistent cross-article image reuse, and any captured update target; record passing image history, then create a content hash and action-specific approval phrase.
- `scripts/build_publish_docx.py` and `scripts/verify_publish_docx.py`: generate the one approved final-upload Word format and fail closed on theme colors, default Word styles, font drift, wrong first-page order, missing image alt text, or layout-token drift.
- `scripts/shopify_publish.py`: perform a safe dry run, capture an existing update target, list blogs, validate Blog Filter/template organization, enforce bounded throttle backoff and the daily new-article limit, reject duplicate creates or stale updates, and create/update the approved Shopify article through the GraphQL Admin API.

Do not bypass a script blocker manually. Fix the artifact or configuration and rerun it.

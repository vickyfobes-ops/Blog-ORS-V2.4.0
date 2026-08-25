# Blog—ORS—V2.4.3 release lock

This file is the merchant-approved, fail-closed contract for this release. The detailed references remain authoritative for implementation. If any generated artifact conflicts with this lock, stop and fix the artifact; never silently downgrade, improvise, or substitute a generic workflow.

## Canonical baselines

- Public Shopify article structure baseline: `https://originsculpture.com/blogs/news/sculpture-finish-guide`, verified 2026-08-21. Its live H1 is `Sculpture Finish Guide: Choosing Bronze, Stainless Steel, Stone and Fiberglass Finishes` and its topic-specific experience section is `How Origin Sculpture Controls a Finish from Physical Sample to Final Inspection`.
- Word format baseline: the accepted final-upload document represented by `assets/format-reference/latest-format-page-1.png` and generated only by `scripts/build_publish_docx.py`.
- Preserve the current Origin site structure and editorial rhythm; optimize content for SEO/GEO and reader decisions without replacing the approved visual format with Word defaults, a generic report, or a decorative review template.

## Locked installation reliability gate

- After every fresh installation or version update, run `scripts/self_test.py` with the Codex workspace document Python runtime. It must return `PASS` before the Skill handles a production article.
- The self-test must use only the installed copy and an isolated temporary directory. It must pass a valid bundle, reject an invalid editorial/image bundle, build and structurally verify the final-upload DOCX, reject a tampered-font DOCX, render the document, and keep the locked first-page typography/layout difference within the script threshold.
- The self-test never reads credentials, calls Shopify, uploads files, creates an article, or modifies a production bundle. A missing document renderer, font asset, runtime dependency, or failed negative test is a release blocker—not a reason to skip the gate.

## Locked operator workflow

1. One topic starts research and drafting.
2. Deliver the complete article and final-upload DOCX for merchant review. End in `AWAITING_APPROVAL`; do not publish in the same turn that first presents new or materially revised bytes.
3. Create, save as draft, or update only after the exact current hash-bound phrase from `approval.json` is supplied.

Any content, metadata, link, image, source, or target change invalidates the old hash and approval phrase.

## Locked content rules

- Public copy is natural American English; planning and review notes are Chinese by default.
- Classify before drafting: Pillar Blog `1,800–2,500` useful body words; Supporting Blog `1,000–1,600`. The declared tier is a hard gate.
- Also classify `editorialMode` before drafting. `site-led` covers custom process, ordering, service, company, and working-with-Origin topics; it is written for ordinary buyers, grounded in current Origin site pages, and keeps technical/process explanation to about `20–30%`. `expert-led` covers materials, finishes, trends, inspiration, maintenance, installation, and site planning; professional terms are allowed when they are useful, but define them on first use and connect each one to a customer decision.
- Answer the governing question within the first 80 words. Use one theme-rendered H1, decision-led H2s, parallel H3s, useful comparison/checklist devices, concise genuine FAQs, and a restrained project CTA.
- Optimize for one reader task. Add three to eight natural long-tail/supporting queries only where they improve clarity; never stuff exact-match phrases.
- Keep one evidence-backed, topic-specific Origin experience section at `10–20%` of body words. Its heading must change with the topic; `Why Choose Origin` is forbidden.
- Relevant experience may include material selection, finish approval, a physical/control sample, production sequence, QC/inspection, installation environment, packing, handover, or maintenance checks. Use only verified Origin or user-provided evidence. Never invent a project, client preference, measurement, result, price, lead time, warranty, certification, factory statistic, material grade, or service scope.
- Technical statements require current authoritative sources and claim mapping. Origin product pages prove visible Origin offerings only; they are not independent technical evidence.

## Locked internal-link rules

- Use at least five unique contextual Origin URLs in the body: at least three distinct, topically relevant `/products/` URLs and normally at least two relevant `/blogs/` URLs.
- Use only canonical URLs from the current live sitemap. Never guess handles or use tracking, search, preview, or collection-prefixed duplicate URLs.
- Distribute links across at least three article sections and product links across at least two sections. Use varied descriptive anchors. Do not cluster links, repeat mechanical anchor formulas, add raw URL lists, use `click here`, or force an irrelevant product to meet a count.

## Locked image rules

- Normally use four to eight useful images including the cover. AI-generated photorealistic environment, material, and process scenes are the default primary visual system: at least `60%` of the image manifest, with the cover normally a generated environment scene.
- Do not use a laptop, phone, webpage, storefront UI, gallery grid, visible logo, watermark, or generated text as the primary scene. Reject obvious anatomical, scale, material, fabrication, or installation errors during visual QA.
- Use no more than two Origin-owned product/project images by default, only as relevant evidence. Generated scenes must be disclosed as editorial examples and must never be described as completed Origin projects or client installations.
- Record `visualQa.inspected`, `visualQa.noScreenUiTextLogo`, `visualQa.realisticMaterialScale`, and `visualQa.sectionRelevant` as true for every approved asset only after visual inspection. Any missing or false value blocks preparation.
- Images need specific alt text, stable slots, exact public-heading placement, PNG for Word, and WebP for Shopify. Distribute images by reader need rather than clustering them.

## Locked Word format

- Visible content only: cover, one public title, article prose, H2/H3, tables, lists, contextual links, and approved images. Exclude SEO notes, sources, review banners, metadata tables, approval codes, headers, footers, page numbers, watermarks, comments, tracked changes, and extra cover/review pages.
- Every visible character is black `#000000`. Hyperlinks are black with a single underline.
- Use only the custom Origin styles: `Origin Title` (Libre Baskerville 33 pt), `Origin H2` (Libre Baskerville 27 pt), `Origin H3` (Libre Baskerville 16.5 pt), `Origin Body`/`Origin Bullet`/`Origin Number` (Poppins 12.5 pt), and `Origin Publish Table` (Poppins 10.5 pt). Embed bundled Libre Baskerville and Poppins regular and bold. A system-font fallback is a blocker even if the declared style name looks correct.
- US Letter; margins 0.72 in top/bottom and 0.90 in left/right. First visible block is a 6.7 in cover, immediately followed by the black public title and black Poppins opening prose.
- Body images default to 5.5 in. The final `project-review` image defaults to 4.5 in and stays with the complete closing CTA section. Fix blank pages, sparse orphan final pages, orphan headings, clipped tables, missing images, and font fallback before review.
- `scripts/build_publish_docx.py` is the only generator. `scripts/verify_publish_docx.py --bundle` and full-page rendered visual inspection are mandatory. If the workspace document runtime, bundled fonts, renderer, builder, or verifier is unavailable, stop the DOCX step; never use a generic Word style or ad hoc fallback.

## Locked Shopify organization and publishing rules

- Default blog is `news`. Assign one focused store-approved Blog Filter by dominant reader task. Use `templateSuffix: null` unless a live alternate article template is merchant-confirmed and allowlisted; never guess or create a template.
- Use the official Shopify GraphQL Admin API and minimum required scopes: `read_content`, `write_content`, `read_files`, and `write_files`. Store credentials only in protected environment configuration, never in the Skill, bundle, Git, chat, screenshots, or logs.
- `确认发布 <handle> <hash8>` creates one live article; `确认保存草稿 <handle> <hash8>` creates one draft; `确认更新 <handle> <hash8>` updates only the freshly captured Article ID and fingerprint while preserving handle and publication state.
- A create bundle never overwrites an article. Reject duplicate handles, stale update fingerprints, wrong stores/blogs, changed source bytes, unsafe HTML, missing alt text, broken/canonical-link failures, unresolved business inputs, and GraphQL user errors.
- Retry only explicit HTTP 429 or GraphQL `THROTTLED` responses with `Retry-After` and bounded exponential backoff. Never automatically retry `articleCreate` or `articleUpdate` after an ambiguous mutation response; reconcile the handle or fingerprint first.
- Default maximum is three new live articles per Shopify store day, counted in the store timezone and checked before upload and again under a local lock before creation. Drafts and edits to already-published articles do not consume the new-live-article allowance.

## Enforcement map

- `scripts/site_inventory.py` locks canonical URL discovery.
- `scripts/self_test.py` locks install-time positive/negative bundle behavior, portable DOCX generation, font rejection, rendering, and first-page visual regression.
- `scripts/prepare_bundle.py` locks tier length, experience ratio/evidence, structure, HTML safety, links, image manifest, metadata, update target, hashes, and action-specific approval phrases.
- `scripts/build_publish_docx.py` plus `scripts/verify_publish_docx.py` lock the approved Word appearance and content order.
- `scripts/shopify_publish.py` locks store identity, Blog Filter/template handling, exact approval, duplicate/stale-target protection, API backoff, mutation non-retry, and the daily live-publication cap.

Do not bypass any blocker manually. Fix the source, evidence, bundle, configuration, or runtime and rerun the controlling script.

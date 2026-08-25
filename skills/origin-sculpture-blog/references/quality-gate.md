# Pre-publish quality gate

## Blockers

- The bundle does not contain all required source artifacts.
- Metadata is missing, the handle is invalid, or the target domain is not explicit.
- Blog Filter is missing/invalid, no longer matches the live Shopify definition, or a custom template suffix is not confirmed in the protected allowlist.
- A live publication would exceed the protected daily store limit, or an explicit Shopify throttle remains after the bounded retry budget.
- The body contains H1, document-shell tags, scripts, forms, iframes, event handlers, or unsafe URLs.
- The opening does not provide useful prose before the first H2.
- A placeholder, invented business fact, preview/staging URL, or unresolved input marker remains.
- Fewer than five unique same-site contextual links appear in the body.
- Fewer than three unique, topically relevant same-site product links appear in the body and link plan.
- Five or more internal links occupy fewer than three article sections, or the required product links occupy fewer than two article sections.
- A planned link is absent from the article, is not in the current sitemap inventory, has a tracking query, or fails live validation.
- A non-cover image placement does not identify an exact public H2/H3 using `Before <heading>` or `After <heading>`, or its slot is missing from the publishable HTML.
- Technical content lacks at least two authoritative non-Origin sources and claim mapping.
- `contentTier` is missing/invalid, a Pillar Blog falls outside 1,800–2,500 words, or a Supporting Blog falls outside 1,000–1,600 words.
- `editorialMode` is missing or is not exactly `site-led` or `expert-led`.
- An image asset lacks `sourceType`/`visualRole`, generated editorial images are below 60%, the cover is not an environment scene, or more than two images default to product-evidence. A non-generated cover produces a warning and requires visual review; AI imagery must still remain the majority.
- Visual QA finds a laptop/phone screen, webpage, storefront UI, gallery grid, visible logo, watermark, generated text, or an obvious anatomy/material/fabrication/installation error as the primary scene.
- The Origin experience marker pair is missing/duplicated, the marked section is outside 10–20% of body words, lacks a dynamic heading/clear Origin attribution, or connects fewer than two topic-relevant experience signals.
- The marked section uses `Why Choose Origin`, lacks a live Origin/user-provided evidence entry, or turns general industry practice into unsupported first-hand company experience.
- The Shopify target does not match the approved site, source files changed after preparation, the confirmation phrase is stale, or the handle already exists.
- An update bundle lacks `update-target.json`, targets a different Article ID/blog/handle, or the remote article fingerprint changed after review.

## Editorial checks

- The article answers one dominant reader task.
- The first 80 words contain the direct answer or governing choice.
- Recommendations include conditions, limitations, and maintenance implications.
- Material, finish, coating, environment, and installation are not conflated.
- Tables and lists simplify a real comparison rather than pad the page.
- Product links are editorially earned, distributed across the article, and explained in `link-plan.json`.
- Product and article links are not concentrated into one sales paragraph and do not reuse mechanical anchor text.
- At least two article links advance the next reader task when relevant.
- Anchor text is descriptive and non-repetitive.
- Claims from Origin pages are labeled as Origin-specific rather than independent facts.
- The Origin experience section resolves a topic-specific decision and reads as practical evidence, not a generic brand advertisement.
- A `site-led` process/service article is understandable to a non-specialist, is grounded in current Origin site content, and keeps technical/process explanation to about 20–30%; it does not read like an internal SOP or engineering manual.
- An `expert-led` material/trend/inspiration/maintenance/installation article may use professional terminology, but defines it at first use and connects it to a visible, care, cost, approval, or site consequence.
- The CTA follows useful guidance and requests only information needed for the next step.
- The conclusion adds a decision rule or next action instead of repeating the outline.

## Search presentation checks

- SEO title is normally 45–65 characters.
- Meta description is normally 140–165 characters and states utility rather than hype.
- The handle is concise and aligned with the primary query.
- Blog Filter represents the article's dominant reader task; incidental keywords do not create noisy secondary classifications.
- The public title, SEO title, and opening answer describe the same promise.
- Image briefs specify scene/function, aspect ratio, and useful alt text.
- AI-generated photorealistic scenes are the primary visual system; Origin-owned images are used sparingly as evidence. Generated scenarios are disclosed in `image-plan.md` and never represented as completed Origin projects.

## Word artifact checks

- The final-upload DOCX contains the approved public title, article body, tables, lists, links, and images only; it contains no review banner, metadata table, source appendix, approval code, header, footer, page number, or watermark.
- All visible text, including hyperlinks and table text, is black. Links remain distinguishable by underlining.
- Typography and spacing follow `references/word-output.md`; headings do not become stranded at a page bottom, tables do not clip or split rows, and every embedded image has alt text.
- Libre Baskerville regular/bold and Poppins regular/bold are all embedded. Any heading fallback to a sans-serif system font is a blocker.

Length ranges are hard gates by declared tier: Pillar Blog 1,800–2,500 words; Supporting Blog 1,000–1,600 words. Useful clarity still matters more than reaching the upper bound.

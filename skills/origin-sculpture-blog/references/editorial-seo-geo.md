# Editorial, SEO, and GEO standard

## Choose one dominant reader task

- Direct answer: definition, maintenance, lifespan, location, or one focused question.
- Buyer decision: material, finish, cost, scale, supplier, installation, or comparison.
- Manufacturer expertise: design development, casting, fabrication, polishing, samples, quality control, packing, or installation coordination.
- Space guide: hotel, garden, residence, plaza, office, resort, or climate-specific placement.
- Case study: verified problem, constraints, decisions, process, installation, and outcome.
- Entity/list: named artists, works, styles, or destinations supported by authoritative sources.

Do not merge models merely to make the article longer.

## Choose the content tier before outlining

- `pillar` (1,800–2,500 words): use for a durable cluster hub that addresses several connected decisions and can support multiple narrower articles.
- `supporting` (1,000–1,600 words): use for one specific question, comparison, material, setting, process step, or care task.

Let the reader task determine the tier. A narrow topic should remain useful and focused rather than being padded into a pillar.

## Choose the editorial mode before outlining

Use exactly one mode and record it in `meta.json`:

- `site-led`: custom sculpture process, how to order, service, company, consultation, and working-with-Origin topics. Write for a buyer who is not an engineer. Build roughly 70–80% of the article around customer questions and current Origin site content: what the reader chooses, what information to send, what they can review, which products or examples clarify the choice, and what happens next. Keep technical or production explanation to about 20–30%. Explain unavoidable terms immediately and remove internal SOP detail that does not change a customer decision.
- `expert-led`: materials, finishes, trends, inspiration, maintenance, installation, environment, and site-planning topics. Use precise professional terms when they reduce risk or improve a choice, but define each term at first use and state its visible, cost, care, or installation consequence in plain English.

Do not let a process/service article become a fabrication textbook. Do not make a maintenance or installation guide vague merely to sound simple.

## Best-performing decision structure

Adapt this sequence to the topic:

1. SEO title, page title/H1, handle, meta description, and concise summary.
2. Opening answer in the first 80 words: state the governing decision and the main tradeoff.
3. Quick comparison or recommendation table for readers who need an immediate orientation.
4. Decision criteria: site, climate, viewing distance, touch, light, maintenance tolerance, budget, and desired aging.
5. Options by material/process/setting, with a consistent mini-pattern: appearance, best fit, limitation, maintenance implication, and sample/product evidence.
6. Cross-option comparison by real project scenario.
7. Specification or approval checklist that a buyer can send to a manufacturer.
8. Common mistakes and how to prevent them.
9. Concise FAQ for genuine follow-up queries.
10. Contextual next step linked to a relevant guide, product/sample, collection, or inquiry action.

This is a default, not a mandatory ten-section template. Remove any section that does not reduce uncertainty.

## SEO rules

- Assign one primary query and 3–8 natural supporting or long-tail query phrases. Use close variants where they read naturally; never repeat exact-match strings merely for density.
- Make title, H1, opening answer, one H2, meta description, and image alt text mutually consistent without repeating the same sentence.
- Treat the public page title/H1 and SEO title as related but separate fields. The H1 may be more descriptive; the SEO title is normally 45–65 characters. If the merchant explicitly approves a longer SEO title, preserve it and report possible search-result truncation as a warning rather than silently rewriting it.
- Keep the handle short, descriptive, lowercase, and stable.
- Use descriptive anchors that name the reader's next task or the referenced product/finish.
- Build topic-cluster paths: this article should point to relevant older guides, and the publishing notes should identify older pages that could later link back.
- Use canonical production URLs without UTM parameters, search parameters, Shopify preview tokens, or collection-prefixed duplicate product paths.
- Never promise rankings, indexing, snippets, or AI citations.

## GEO rules

Write passages that can be accurately extracted without losing their conditions:

- Put the direct answer before brand promotion.
- Use explicit entities and nouns instead of vague pronouns.
- State conditions and exceptions next to recommendations.
- Separate facts, Origin Sculpture practice, and editorial recommendations.
- Use compact comparison tables, labeled checklists, and short answer-first FAQs where useful.
- Cite original/authoritative sources near technical or time-sensitive claims in the review Markdown; keep a clean source ledger even when the public site's preferred style places source links contextually.
- Use verifiable experience signals: approved samples, drawings, weld finishing, patina control, coating specification, packaging, site photos, and maintenance instructions. Do not fabricate first-hand experience.

## Image evidence rules

- Use AI-generated photorealistic environment, material, and process scenes as the primary visual system: at least 60% of the approved image manifest and normally the cover. They should show sculpture in believable residential, hospitality, garden, plaza, workshop, delivery, or installation contexts that support the surrounding section.
- Do not make a laptop, phone, webpage, storefront UI, gallery grid, text panel, visible logo, or watermark the subject. Avoid generated typography entirely. Reject impossible material behavior, tools, anatomy, rigging, bases, or scale during visual QA.
- Use two or three current, directly relevant Origin-owned product, installed-setting, workshop, sample, packing, or installation images in every article. Their role is site-specific evidence, not a substitute for the AI scene system, which must remain at least 60% of the image manifest.
- Never describe generated imagery as a completed Origin Sculpture project, client installation, case study, or proof of a business claim.
- In `image-assets.json`, label every item with `sourceType` (`generated-editorial`, `origin-owned`, or `user-provided`) and `visualRole` (`environment-scene`, `process-scene`, `material-detail`, or `product-evidence`). Give every meaningful image specific alt text describing what the reader can actually see.

## Add topic-specific Origin experience

Reserve roughly 10–20% of the article for one marked, evidence-backed Origin Sculpture experience section. Make the heading and advice change with the topic—for example, finish articles may focus on physical sample approval and production comparison; maintenance articles may focus on inspection access and care handover; installation articles may focus on site conditions, packing, lifting, anchoring, or drainage checks.

State what Origin Sculpture actually reviews or recommends only when a live Origin page or user-provided evidence supports it. Separate verified Origin practice from general technical guidance. Avoid a reusable `Why Choose Origin` block, catalog-style promotion, invented projects, numerical performance claims, and implied client preferences.

## Technical precision for finish articles

Distinguish these layers:

1. substrate/material, such as 316L stainless steel, cast bronze, marble, limestone, or FRP;
2. fabrication and surface preparation;
3. visual finish, such as mirror, brushed, honed, bush-hammered, patinated, gloss, satin, or matte;
4. coating or sealer, if any;
5. exposure and use conditions;
6. cleaning, inspection, and renewal plan.

Describe how light, fingerprints, water spotting, dirt retention, repair visibility, natural variation, UV, moisture, salt, freeze-thaw exposure, touching, and viewing distance affect the decision. Avoid universal claims. Require a representative control sample that records color, gloss, texture, direction, and acceptable variation.

## Style exclusions

Avoid:

- generic openings about art transforming spaces;
- a separate `Introduction` heading;
- repeated `luxury`, `timeless`, `elevate`, `stunning`, `perfect`, and `investment` language;
- unsupported lifespan claims or “maintenance-free” claims;
- fabricated named projects, client quotations, or factory statistics;
- overlong conclusions that restate every section;
- FAQs written only to repeat keywords;
- product grids inserted without editorial context.

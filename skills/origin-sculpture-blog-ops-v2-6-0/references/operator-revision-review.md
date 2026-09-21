# Operator revision review

Use this review mode when an operator has edited a generated article, supplied a revised DOCX/HTML/Markdown file, or changed a Shopify draft/live article and the user wants to learn from the edit.

## Purpose and boundary

The outcome is an evidence-bound change record, not an automatic rewrite of the editorial system. A single operator edit can be useful for its article without becoming a global rule or a new Origin business claim.

## Inputs to capture

Compare the earliest available approved/generated version with the operator-edited version. When available, also capture the current Shopify article or draft state. Preserve the source paths, retrieval dates, Article ID, handle, blog, and publication status in the review record.

Inspect, at minimum:

- SEO title, public title/H1, handle/slug, tags, Blog Filter, and template suffix;
- opening answer, headings, deleted/added/re-written paragraphs, factual claims, scope terms, and CTAs;
- internal links, images, alt text, and image placement; and
- Shopify state, including whether the evidence proves a draft, an update, or an actual live publication.

Do not claim an operator changed a field merely because it exists in the revised file. It must differ from the compared version or have a separately recorded operator instruction.

## Required record

Write `<run-dir>/operator-revision-record.md` in Chinese with these sections:

1. **Comparison objects and dates** — every source artifact and Shopify state inspected.
2. **Observed edits** — for each material difference, give before text/state, after text/state, evidence source, and a restrained explanation of the likely editorial purpose.
3. **Limited reusable signals** — patterns that may be reused only when topic-relevant and supported by current sources or explicit operator input.
4. **Local-only changes** — exact wording, structure, examples, service boundaries, or technical details that remain confined to the reviewed article.
5. **Prohibited inferences** — facts or requirements that cannot be inferred from the revision.
6. **Pending operator questions** — business-scope, technical, image, link, or publication questions that need confirmation before they become reusable.
7. **Promotion decision** — either `record only`, `propose promotion`, or `promote with explicit user approval`, with the evidence for that decision.

## Classification rules

### Actual edit

Use only for a verified before/after difference. Do not turn an interpretation into an actual edit.

### Limited reusable signal

Use for a pattern that improves a similar reader decision and is supported by current evidence. It must include its conditions, for example: “for custom-process articles, when installation scope is verified.”

### Local-only change

Use for a one-article heading, an eight-step structure, a material sequence, a base/anchor example, a named delivery field, or an article-specific service statement. Keep it out of global drafting requirements.

### Prohibited inference

Use whenever a revision could be mistaken for a site-wide business, technical, pricing, warranty, service, publishing, link, or media rule. State the forbidden inference explicitly.

## Evidence and Shopify safety

- An Origin page proves only what it visibly supports. A revised article is not independent evidence of company-wide practice.
- A claim about installation scope, on-site work, pricing, lead time, shipping, warranty, repair, material grade, or technical responsibility requires current Origin evidence or explicit operator confirmation.
- Base plates, anchors, foundations, embedment, grout, loads, local-code references, and fabrication sequences must be presented as project-specific concepts unless authoritative/project evidence proves more.
- A saved Shopify draft is not a live publication. Do not infer publish approval from a draft, updated handle, uploaded image, or captured update target.
- An observed internal link, image, alt text, Blog Filter, tag, handle, or template does not create a new global standard unless the user explicitly approves it.
- This review mode is read-only with respect to Shopify unless the user separately supplies the current exact create/update/draft confirmation phrase.

## Promotion rule

Keep each revision in its own record first. Promote a lesson into `operator-editing-rules.md` only when either:

1. the user explicitly asks to promote this reviewed rule; or
2. multiple approved revision records demonstrate the same pattern and its limits.

When promoting, write the conditions and prohibited inferences beside the rule. Never use promotion to weaken the existing evidence, quality-gate, or Shopify approval requirements.

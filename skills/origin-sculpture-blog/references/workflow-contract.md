# Workflow and artifact contract

## State machine

1. `TOPIC_RECEIVED`: one concrete topic exists.
2. `RESEARCHING`: current sources and the live Origin sitemap are being checked.
3. `AWAITING_APPROVAL`: a complete bundle passed the gate and has hash-bound confirmation phrases.
4. `REVISING`: user feedback or a supplied document changes the approved bytes; return to preparation.
5. `PUBLISHING` or `UPDATING`: an exact current phrase authorizes one matching Shopify mutation.
6. `PUBLISHED`, `SAVED_AS_DRAFT`, or `UPDATED`: report the returned Shopify record.

Never jump from `TOPIC_RECEIVED` to `PUBLISHING`. Never infer approval from silence, compliments, or a generic confirmation.

## Run directory

Use `origin-blog-runs/<handle>/` under the user's working directory. Keep the complete review and publication record together.

## `meta.json` schema

```json
{
  "siteDomain": "originsculpture.com",
  "blogHandle": "news",
  "title": "Public article title rendered as H1 by the Shopify theme",
  "seoTitle": "Search title",
  "metaDescription": "Search description",
  "handle": "lowercase-hyphenated-handle",
  "author": "Origin Sculpture",
  "publicationAction": "create",
  "contentTier": "pillar",
  "tags": ["Buying Guide", "Sculpture Finish"],
  "blogFilters": ["Sculpture Materials Knowledge Center"],
  "templateSuffix": null,
  "coverImage": {
    "url": "https://publicly-fetchable-image.example/image.webp",
    "alt": "Specific descriptive alt text"
  }
}
```

`publicationAction` is `create` for a new article and `update` only when the user explicitly asks to modify an existing Shopify article. An update bundle must contain a freshly captured `update-target.json` with the exact Article ID, current handle/blog, publication state, and remote fingerprint. Keep the existing handle unless the user separately authorizes a URL change and redirect plan.

`contentTier` is required:

- `pillar`: a broad topic-cluster hub with 1,800–2,500 public body words;
- `supporting`: one narrow reader task with 1,000–1,600 public body words.

Choose the tier from search intent and scope before drafting. Do not select a tier after writing merely to make an out-of-range article pass.

`blogFilters` accepts one primary value and at most one genuinely useful secondary value from the live Origin choices:

- `Project Inspiration`
- `Sculpture Buying Guide`
- `Sculpture Materials Knowledge Center`
- `Sculpture Design Inspiration`
- `Sculpture Manufacturing & Craftsmanship`
- `Sculpture Trends`
- `Sculpture Maintenance Guide`

Choose by the dominant task. Material/finish comparisons belong in `Sculpture Materials Knowledge Center`; cleaning and preservation belong in `Sculpture Maintenance Guide`; price, ordering, placement, and procurement decisions belong in `Sculpture Buying Guide`. `prepare_bundle.py` infers one primary filter only for a legacy bundle that omits `blogFilters` and reports the inferred choice in `qa.json`.

Use `templateSuffix: null` for the theme's default article template. Set a custom suffix only when it is visible in the live Shopify theme and included in the protected template allowlist. The Skill does not create or edit theme templates.

`coverImage` may be omitted during review. Treat a missing cover as a warning, not a blocker, unless the user or site policy requires one. Never put secrets in `meta.json`.

When the bundle uses local images, use `image-assets.json` instead of a public `coverImage` URL. Include one `cover` slot and one entry for every inline image:

```json
[
  {
    "slot": "cover",
    "png": "images/article-cover.png",
    "webp": "images/article-cover.webp",
    "placement": "Shopify article cover image",
    "alt": "Specific descriptive alt text"
  }
]
```

`png` is required for the portable Word artifact and is hash-bound with the review bundle. `webp` is required and is the only format published to Shopify. Every non-cover `placement` must be `Before <exact public H2/H3>` or `After <exact public H2/H3>`. Reference inline assets in `article.html` as `origin-asset://<slot>`. The publisher uploads the approved WebP bytes to Shopify Files after confirmation, replaces only those placeholders in memory, and uses the `cover` slot as the article image. Do not use a local filesystem path in publishable HTML.

## `link-plan.json` schema

```json
[
  {
    "url": "https://originsculpture.com/products/example",
    "type": "product",
    "anchor": "mirror-polished stainless steel finish sample",
    "relevance": "Lets the reader inspect the exact finish discussed in the surrounding selection advice."
  },
  {
    "url": "https://originsculpture.com/blogs/news/example",
    "type": "article",
    "anchor": "stainless steel sculpture care",
    "relevance": "Continues the reader's task from finish selection into maintenance."
  }
]
```

Each planned URL must appear in `article.html`. Use at least five unique Origin Sculpture URLs, including three distinct products and normally two related articles.

## `sources.md` contract

List the retrieval date and map each source to the claims it supports. Example:

```markdown
# Sources

Retrieved: 2026-08-18

- [Nickel Institute: source title](https://example.org/source) — supports the distinction between brushed and mirror stainless finishes.
```

Use at least two authoritative non-Origin sources for a technical article. More sources are not automatically better; every source must support a claim that appears in the article.

Add a dedicated evidence ledger for the marked Origin experience section:

```markdown
## Origin experience evidence

- [Origin Sculpture: verified sample page](https://originsculpture.com/products/example) — supports the statement that a physical finish option is available for review.
- [USER-PROVIDED EVIDENCE: approved QC checklist, 2026-08-19] — supports the described inspection sequence; keep the private file out of the public article.
```

At least one entry must be a current `originsculpture.com` page or clearly labeled user-provided evidence. A product/sample page supports only what it visibly shows; it does not prove an unnamed project, client preference, performance result, or company-wide process.

## HTML contract

- Store only the body in `article.html`; do not include `html`, `head`, `body`, or H1 tags.
- Allow semantic article tags such as `p`, `h2`, `h3`, `ul`, `ol`, `li`, `table`, `thead`, `tbody`, `tr`, `th`, `td`, `strong`, `em`, `a`, `img`, `figure`, `figcaption`, `blockquote`, `div`, `br`, and `hr`.
- Do not include scripts, forms, iframes, embedded trackers, event-handler attributes, or `javascript:` URLs.
- Use absolute canonical URLs in publishable HTML.
- Give every meaningful image a specific alt attribute. Use empty alt only for a truly decorative image.
- Wrap exactly one topic-specific Origin Sculpture experience section in `<!-- origin-experience:start -->` and `<!-- origin-experience:end -->`. Shopify does not render these comments. The enclosed visible text must be 10–20% of total public body words, include a dynamic H2/H3, attribute the practice to Origin Sculpture, and connect at least two relevant experience signals.
- Do not use `Why Choose Origin` or `Why Choose Origin Sculpture` as the marked section heading.

## Approval binding

`prepare_bundle.py` verifies that the public article text in `article.md` matches `article.html`, adds the approved/inferred Blog Filter to the publication payload, then hashes `meta.json`, `article.md`, `article.html`, `summary.html`, `sources.md`, and `link-plan.json`. When present, it also hashes `image-assets.json`, every referenced WebP, and `update-target.json`. `shopify_publish.py` rechecks those hashes. Editing any source file, approved image, or captured update target invalidates the confirmation phrase.

The phrase determines the mutation and mode; the content hash determines the article version. New publications reject duplicate handles. Existing-article updates require `确认更新 <handle> <hash8>`, preserve the handle and current publication state, and block when the captured Article ID, blog, handle, or remote fingerprint no longer matches Shopify.

## Runtime publication limits

Use Shopify's store timezone for daily live-publication accounting. Default to three live articles per store day and allow protected configuration from one through ten. Count all articles already live that store day, regardless of whether a person, another app, or this Skill published them. Do not count drafts.

Treat Shopify's explicit HTTP 429 or GraphQL `THROTTLED` response as retryable using bounded exponential backoff and `Retry-After` when supplied. Never blindly retry `articleCreate` or `articleUpdate`. Recheck the handle after an ambiguous create failure; recheck the target fingerprint after an ambiguous update failure before any new authorized attempt.

# Shopify setup and safe publication

## Requirements

Create an app in Shopify Dev Dashboard or use an existing admin-created custom app. Shopify no longer permits new admin-created custom apps. Request only `read_content`, `write_content`, `read_files`, and `write_files`. Content access supports blog discovery, duplicate-handle checks, and `articleCreate`; Files access supports approved cover and inline-image uploads. Confirm the current scopes and API version in official Shopify documentation when installing.

Set credentials in the environment, never in the Skill or article bundle:

```bash
export SHOPIFY_STORE_DOMAIN="your-store.myshopify.com"
export SHOPIFY_API_VERSION="2026-07"
export SHOPIFY_BLOG_ID="gid://shopify/Blog/123456789"
export SHOPIFY_PUBLIC_DOMAIN="your-public-domain.com"

# Optional: comma-separated suffixes already present in the live theme.
# Leave blank to use only Shopify's default article template.
export SHOPIFY_ARTICLE_TEMPLATE_SUFFIXES=""

# Safety default: at most 3 live articles per Shopify store day.
# Allowed protected configuration range: 1–10. Drafts do not count.
export SHOPIFY_MAX_LIVE_ARTICLES_PER_DAY="3"

# Use one authentication method:
export SHOPIFY_ADMIN_ACCESS_TOKEN="shpat_..."
# or, for an app owned by the same organization as the store:
export SHOPIFY_CLIENT_ID="..."
export SHOPIFY_CLIENT_SECRET="..."
```

`SHOPIFY_BLOG_ID` is optional when the approved `blogHandle` uniquely identifies a blog. The script can discover it. The API version is intentionally explicit so an installer must review it rather than silently relying on a stale version.

The publisher automatically loads `~/.config/origin-sculpture-blog/shopify.env`, or the path in `ORIGIN_SHOPIFY_ENV_FILE`. Keep that file outside the repository and set mode `600`. Environment values take precedence. Never save a token or client secret in shell history, Git, `meta.json`, screenshots, chat messages, or command output.

Client credentials are exchanged in memory for a 24-hour access token on each run. This flow is only for apps owned by the same organization as the target store. For another merchant's store, complete Shopify's OAuth/CLI installation flow and provide its Admin API access token instead.

### Shopify CLI credentials

For an app linked with Shopify CLI, the publisher also accepts the CLI names `SHOPIFY_API_KEY` and `SHOPIFY_API_SECRET` as aliases for `SHOPIFY_CLIENT_ID` and `SHOPIFY_CLIENT_SECRET`. Prepare the protected file with the store-specific values above, then merge the linked app credentials without printing them:

```bash
chmod 600 ~/.config/origin-sculpture-blog/shopify.env
shopify app env pull --env-file ~/.config/origin-sculpture-blog/shopify.env --no-color
```

Run this from the linked Shopify app project. The app must already be installed on the target store and its released version must request `read_content`, `write_content`, `read_files`, and `write_files`. Never paste the secret into chat or commit the protected file.

## Verify the store, scopes, and blog

```bash
python scripts/shopify_publish.py \
  --bundle <run-dir> \
  --verify-store
```

The check is read-only. It verifies the actual `.myshopify.com` identity, public-domain mapping, required scopes, API version, and available blog handles without printing credentials.
It also returns the live `custom.blog_filter` choices and the locally allowlisted article-template suffixes. Discover/create alternate templates in Shopify Admin under Online Store → Themes → Edit theme → Blog posts. Add only confirmed suffixes to `SHOPIFY_ARTICLE_TEMPLATE_SUFFIXES`; no `read_themes` permission is required for the default-only workflow.
It reports the Shopify store timezone, today's live-article count, remaining daily allowance, and throttle-retry policy. The daily count is store-wide and includes articles published outside the Skill.

### Verify the rendered page title before live publication

The bundle gate proves `article.html` has no H1; it cannot prove the storefront theme renders the article title correctly. For the selected `templateSuffix` (including the default), identify a current published article that uses that same template. Inspect its rendered public HTML/DOM read-only and confirm there is exactly one visible `<h1>` containing that article's public title. Record the public URL, how the matching template was confirmed, check date, and H1 text in the review notes. Recheck after a theme or article-template change. The `sculpture-finish-guide` page was seen with one H1 on 2026-09-22, but that observation alone does not establish the template for every article.

If no same-template published page is available, or the H1 is missing/duplicated/mismatched, do not execute a live publication or advise the operator to manually publish an existing draft. Escalate the template correction; do not insert an H1 into article body HTML to compensate. An expressly authorized Shopify draft may remain unpublished with the issue disclosed.

## Discover blogs

```bash
python scripts/shopify_publish.py --list-blogs
```

Copy only the selected blog GID into the environment. Do not create a new blog automatically.

## Dry run

After `prepare_bundle.py` passes:

```bash
python scripts/shopify_publish.py --bundle <run-dir> --dry-run
```

The dry run prints a safe summary and the required confirmation phrases. It does not call Shopify.
It also prints the configured daily live-article limit.

## Live creation, draft creation, or existing-article update

Use the exact current phrase shown in `approval.json`:

```bash
python scripts/shopify_publish.py \
  --bundle <run-dir> \
  --confirm "确认发布 example-handle deadbeef"
```

or:

```bash
python scripts/shopify_publish.py \
  --bundle <run-dir> \
  --confirm "确认保存草稿 example-handle deadbeef"
```

For an existing article, first capture the exact target and then, after preparation and review, use its update phrase:

```bash
python scripts/shopify_publish.py \
  --bundle <revision-run-dir> \
  --capture-update-target

python scripts/shopify_publish.py \
  --bundle <revision-run-dir> \
  --confirm "确认更新 example-handle deadbeef"
```

The script uploads hash-approved WebP assets with `stagedUploadsCreate` and `fileCreate`, waits for Shopify CDN readiness, replaces `origin-asset://` placeholders only in memory, then uses `articleCreate`. It supplies SEO title/description through the `global.title_tag` and `global.description_tag` metafields, sets the validated `custom.blog_filter` list, applies an allowlisted template suffix when requested, aborts if the handle already exists, and writes the sanitized response to `publish-result.json`.

For a user-approved revision to an existing article, set `publicationAction` to `update`, capture the target before preparation, review the new hash-bound Word document, then use the exact `确认更新 <handle> <hash8>` phrase. The publisher uses Shopify `articleUpdate` on the captured Article ID, preserves the handle and publication state, and blocks if the remote fingerprint changed after capture.

## Operational safety

- Existing articles are updated only in explicit update mode with a captured Article ID, unchanged remote fingerprint, and exact hash-bound update phrase; a normal create bundle never overwrites an article.
- Shopify HTTP 429 and GraphQL `THROTTLED` responses use at most five bounded exponential-backoff retries, honoring `Retry-After` and waiting no more than 30 seconds per retry.
- `articleCreate` and `articleUpdate` are never automatically retried. This preserves duplicate-handle and remote-fingerprint reconciliation after a possibly ambiguous mutation response.
- New live publication is blocked when the Shopify store has already reached `SHOPIFY_MAX_LIVE_ARTICLES_PER_DAY` for its own timezone. The script checks before asset upload and again under a local lock immediately before creation; drafts and existing-article edits are exempt.
- Image upload begins only after an exact hash-bound create/update confirmation. Matching previously uploaded assets are reused by file hash; new uploads are cached in `asset-upload-result.json`.
- If a request times out after it may have reached Shopify, query the handle for a create or the target fingerprint for an update before retrying.
- A new body, metadata file, summary, source ledger, link plan, image manifest, or approved WebP requires a new preparation hash and phrase.
- A live article uses `isPublished: true`; a draft uses `isPublished: false`.
- The environment store host must match `meta.json.siteDomain` after normalizing `www` and `.myshopify.com` aliases only when explicitly configured for that storefront. For Origin Sculpture, use the store's authorized admin domain while the approved public domain remains `originsculpture.com`.

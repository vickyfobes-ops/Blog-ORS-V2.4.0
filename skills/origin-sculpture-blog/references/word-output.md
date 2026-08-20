# Final-upload Word output

Use this standard whenever the Skill creates the merchant review DOCX. The document is the exact public-article handoff, not an editorial report.

## Visible content

- Include the approved cover, public title, article prose, H2/H3 hierarchy, tables, lists, contextual hyperlinks, and approved inline images.
- Exclude the SEO pack, source ledger, link plan, image-generation notes, review labels, approval codes, comments, tracked changes, headers, footers, page numbers, watermarks, and blank review pages.
- Use the public article title once. Do not add a second H1 inside the body.

## Typography and color

- All visible text is black (`#000000`), including headings, body copy, table text, captions when used, and hyperlinks. Hyperlinks use a single underline instead of blue text.
- Match the Origin article hierarchy: New York for the title and headings when available; Poppins for body, lists, links, and tables. Embed the bundled OFL-licensed Poppins regular and bold fonts.
- Target sizes: title 33 pt, H2 27 pt, H3 16.5 pt, body 12.75 pt, and tables 10.5 pt. Keep body line spacing near 1.7 and preserve the site's generous paragraph spacing.
- Do not substitute a decorative brand treatment, colored review chrome, or a separate cover sheet.

## Layout and accessibility

- Use US Letter pages with restrained margins and no visible header/footer story.
- Place every non-cover image according to its hash-bound `image-assets.json` instruction: `Before <exact H2/H3>` or after the first paragraph under `After <exact H2/H3>`.
- Keep headings with the following paragraph. Prevent table-row splitting, repeat or reproduce table headers on continuation pages, and avoid clipped narrow columns.
- Add specific alt text to every embedded image. Preserve usable external hyperlinks.
- Render or inspect the DOCX after generation. Fix overflow, blank pages, orphan headings, clipped tables, missing images, font fallback that materially changes hierarchy, and any non-black visible text before delivery.

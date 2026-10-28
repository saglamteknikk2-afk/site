# Uploaded SEO package preview — 28 October 2026

This release publishes the user's `saglamkombiklima-seo.zip` on the existing
GitHub Pages site. It does not run the legacy source builder, overwrite the
existing editable application source, or deploy to saglamkombiklima.com.tr.

The reviewed archive SHA-256 is
`702e308fb7c92d08acac2c9a59fe18f8d9b1a39b3643dffeebc54f57168e365a`.
The builder rejects a different archive until it has been reviewed.

## Changes made for this preview

- Keep the uploaded premium design, existing visitor routes, district text,
  technical code tables, and new internal linking sections.
- Correct the active browser resolver's relative route mismatch. Scoped code
  meanings remain tied to the selected model. PHP is not deployed or repaired.
- Replace unsupported local frequency and border claims with neutral wording.
- Correct brand FAQ answers that incorrectly restricted coverage to nine districts.
  Keep visible answers and FAQ JSON-LD in agreement.
- Distinguish actual guide-page counts from multiple document scopes on one URL.
- Remove invented `priceRange` values without inventing an address.
- Keep manufacturer source labels as plain references rather than outbound links.
  Preserve phone/WhatsApp markup; the preview guard disables actual contact actions.
- Omit PHP, administration HTML and runtime/private files. Set every visitor page
  to noindex and block form, location, Telegram and Gemini submissions.
- Recalculate the preview content manifest from the files actually published.
- Preserve the previously delivered `/inceleme/` read-only review route.

## What this does not establish

Adding sections and internal links does not prove that doorway/scaled-content risks
are eliminated or that Google will index a page. A distinct H2 is not proof of
unique utility. Not every neighborhood has an independent content page; the
selection flow still uses the shared service selector. Not every model/code is
verified. The archive retains older installation/removal offers and some foreign
market source guides; these require a separate, deliberate production scope pass.

`llms.txt` is an optional catalogue, not a Google ranking control. FAQ JSON-LD
parsing is not the same as rich-result eligibility. Live PHP, server performance,
Telegram delivery, Gemini responses and Search Console outcomes are not verified
by this static preview release.

## Reproduce

```sh
python preview-release/build_preview.py --output _site
python preview-release/check_preview.py _site
node preview-release/test_routes.cjs _site
```

The dedicated `seo-package-preview.yml` workflow performs these checks before
deploying the uploaded package. Existing source workflows are retained.

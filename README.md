# hugo-azulprint — a Hugo theme

`azulprint` is a quietly icy theme for academic profile sites built with Hugo.

Homepage is composed from **section archetypes** — reusable kinds you can
reorder, toggle, or extend without forking the theme. Seven archetypes ship
out of the box (hero, about, research, publications, awards, posts, contact);
add your own by dropping a partial under `layouts/partials/sections/<kind>.html`.

The `exampleSite/` is populated as [Barbara McClintock's personal site](https://chenyenchung.github.io/hugo-azulprint/)
to give you a feel of how it would look like. Replace its contents with your own when you adopt the theme.

## Quick start

```bash
hugo new site mysite
cd mysite
git init
git submodule add https://github.com/your/hugo-azulprint themes/hugo-azulprint
echo 'theme = "hugo-azulprint"' >> hugo.toml
```

Then copy `themes/hugo-azulprint/exampleSite/` contents into your site root and edit
`hugo.yaml`, `content/_index.md`, etc.

## Content model

Most "data" lives in front matter (YAML) so it's easy to edit without writing
template syntax. Prose sections (about, post bodies) live in Markdown body.

| Section      | Where the data is                          |
|--------------|--------------------------------------------|
| Hero         | `content/hero.md` Markdown body (intro) + front matter (`keywords`); identity in `hugo.yaml` `params.*` — `author`, `email`, `scholar`, `cv`, `portrait` |
| About        | `content/_index.md` Markdown body; optional `aside` in its front matter |
| Research     | `content/research.md` front matter (list of `interests`) |
| Publications | `data/publications.yaml` (DOI list) → per-DOI pages via `scripts/build-publications.py` |
| Awards       | `data/awards.yaml` (entry list) → per-award pages via `scripts/build-awards.py` |
| Posts        | `content/posts/*.md`                       |
| Contact      | `content/contact.md` front matter (list of `links`) |

## Section archetypes

The homepage iterates over `params.sections`:

```yaml
params:
  sections:
    - { kind: hero,         id: hero,         unnumbered: true }
    - { kind: about,        id: about,        page: "/" }
    - { kind: research,     id: research,     page: "research" }
    - { kind: publications, id: publications, page: "publications" }
    - { kind: awards,       id: awards,       page: "awards" }
    - { kind: posts,        id: posts,        section: "posts" }
    - { kind: contact,      id: contact,      page: "contact" }
```

Per-entry keys: `kind` (required, picks the renderer), `id` (anchor), `page`
(content page to read), `section` (Hugo section name for list-style sources),
`data` (data file name), `label` (overrides the section heading on the
homepage; the standalone page — e.g. `/publications/` — keeps its own
`title`), `num` (overrides auto-numbering, e.g. `"Appendix"`),
`unnumbered: true`, `hidden: true`.

Label resolution order: entry `label` → linked page's front-matter `label`
→ i18n key `section_<kind>` → humanized kind. So `{ kind: publications,
label: "Featured publications" }` renames the homepage heading without
touching `/publications/`.

Reorder, hide, or duplicate entries freely. If `params.sections` is unset, the
default list above ships in `data/azulprint_defaults.yaml`.

### Adding a new section

1. Create `layouts/partials/sections/<kind>.html` in your site (Hugo picks
   site-level partials over theme partials automatically).
2. Add an entry to `params.sections` with `kind: <kind>`.
3. Optionally add an i18n key `section_<kind>` for the default label.

The renderer receives a context dict: `kind`, `id`, `num`, `label`, `page`,
`section`, `params` (extra kwargs from the entry), `Site`, `ctx` (root page).

## Theming

```yaml
params:
  palette: "clinical"   # "clinical" | "frost" | "frost-max" | "glacier"
  density: "regular"    # "compact" | "regular" | "airy"
  # accent: "#2a6486"   # optional one-color override
```

All palettes share the same icy, high-contrast register — they differ in how
blue the background pulls and how dark the accent runs. `clinical` is the
most neutral; `frost-max` is the highest-contrast.

## Hero & site identity

Identity bits live in `hugo.yaml`:

```yaml
params:
  author:   "Barbara McClintock, PhD"           # full name + degree (portrait initials fallback)
  email:    "mcclintock@cshl.example"           # mailto link
  scholar:  "https://scholar.google.com/..."    # Scholar profile
  cv:       "/cv.pdf"                           # CV link
  # portrait: "/portrait.jpg"                   # falls back to initials if unset
```

The hero's intro prose and chips live in `content/hero.md`:

```markdown
---
title: "Hero"
keywords:
  - maize cytogenetics
  - transposable elements
build:
  render: never   # don't emit /hero/ as a standalone page
  list: local
---

Hi, I'm *Barbara McClintock* — a cytogeneticist at **Cold Spring Harbor
Laboratory**.
```

The body is rendered as Markdown — author chooses their own greeting. If
`content/hero.md` is absent, the hero still renders the portrait and links.

The About section's optional callout lives in `content/_index.md` front
matter:

```yaml
---
title: "…"
aside:
  label: "currently"
  body: |
    Mapping controlling elements in maize at **Cold Spring Harbor**.
---
```

`aside.body` is rendered as Markdown.

## Publications

`data/publications.yaml` is a DOI list with curation flags. Each entry:

```yaml
- doi: "10.1126/science.15739260"   # required
  featured: true                     # eligible for the homepage section
  alt_text: "…"                      # optional one-line note on cards
  description: "…"                   # optional internal note, not rendered
```

`scripts/build-publications.py` fetches CrossRef metadata (title, authors,
venue, year), writes one Hugo page per DOI under `content/publications/<slug>/`
with `build.render = never` and `build.list = local`, and caches responses
under `data/.crossref-cache/`. Preprints with `10.1101` / `10.48550` DOIs are
labeled "bioRxiv" / "arXiv" automatically.

```yaml
params:
  publications:
    featuredCount: 3                 # top-k newest featured shown on homepage
    authorAliases:                   # author strings to bold in the card list
      - "McClintock, B."
      - "McClintock B"
      - "Barbara McClintock"
```

## Awards

`data/awards.yaml` is a flat entry list. Each entry:

```yaml
- title:    "Nobel Prize in Physiology or Medicine"   # required
  year:     1983                                       # required
  org:      "Nobel Foundation"                         # optional
  category: "award"                                    # "award" | "funding"
  featured: true                                       # homepage eligibility
  alt_text: "…"                                        # optional one-line note
```

`scripts/build-awards.py` writes one Hugo page per entry under
`content/awards/<slug>/` (same `build.render = never` / `build.list = local`
pattern as publications). The `category` field drives chip styling on cards.

```yaml
params:
  awards:
    featuredCount: 3                 # top-k newest featured shown on homepage
```

## Other configuration

```yaml
params:
  postsLimit: 3                                   # homepage post cards cap
  dateFormats:
    postSingle: "January 2, 2006"
    postList:   "Jan 2, 2006"
    postCard:   "02 Jan 2006"
    footer:     "02 Jan 2006"
  linkExternalNewTab: true
  fonts: { url: "" }                              # override Google Fonts <link>
  rss:   { enabled: true }
```

## Override partials (empty by default)

Drop any of these in your site `layouts/partials/` to inject content:

| Partial               | Called from           | Use for                          |
|-----------------------|-----------------------|----------------------------------|
| `head-extra.html`     | start of `<head>`     | preconnects, early styles        |
| `head-custom.html`    | end of `<head>`       | extra meta, structured data      |
| `body-start.html`     | first child of body   | skip-link, analytics             |
| `body-end.html`       | last child of body    | deferred scripts, analytics      |
| `nav-custom.html`     | end of `<nav>`        | extra nav links                  |
| `footer-custom.html`  | end of `<footer>`     | sponsor logos, legal links       |

## Render hooks

Default render hooks ship under `layouts/_default/_markup/` for links,
images, code blocks, and headings. Override any of them in your site to
customize how Markdown content renders.

## i18n

UI strings live in `i18n/en.yaml`. Drop `i18n/<lang>.yaml` in your site and set
`languageCode: <lang>` to localize labels.

## Build scripts

Two sections are page-per-entry: each YAML row becomes a Hugo page with
`build.render = never` and `build.list = local`, so it shows up in the
homepage section and the timeline list page but never produces standalone
HTML.

```bash
python scripts/build-publications.py   # data/publications.yaml → content/publications/<slug>/
python scripts/build-awards.py         # data/awards.yaml       → content/awards/<slug>/
```

`build-publications.py` enriches each DOI from CrossRef and caches the
response under `data/.crossref-cache/`. `build-awards.py` is a pure
YAML → frontmatter transform (no network). Both prune stale auto-generated
pages when entries are removed.

A third helper, `scripts/fetch-publications.py`, bootstraps
`data/publications.yaml` from an ORCID or Google Scholar profile (resolves
each work to a DOI via CrossRef, dedupes against the existing file, and
optionally prompts you to mark entries as featured). Useful once when first
adopting the theme.

## License

MIT

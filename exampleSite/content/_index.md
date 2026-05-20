---
title: "hugo-azulprint — example site"
---

This is the example site for **hugo-azulprint**, a Hugo theme for academic
profile sites. The page is composed from **section archetypes** — `hero`,
`about`, `research`, `publications`, `awards`, `posts`, `contact` — listed
in `params.sections` of `hugo.yaml`. Reorder, hide, or add your own kind by
dropping a partial under `layouts/partials/sections/<kind>.html`.

The sections below this one are dressed up as a stylized
*Barbara McClintock* persona so the archetypes look like real content rather
than lorem-ipsum boxes. When you adopt the theme, replace `content/`,
`data/awards.yaml`, and `data/publications.yaml` with your own.

The visual chrome — corner marks, coordinate labels, dotted grid background,
section rules — is controlled by `params.palette` (clinical / frost /
frost-max / glacier) and `params.density` (compact / regular / airy). See the
[theme README](https://github.com/chenyenchung/hugo-azulprint) for the full
list of params and how to wire up the publications / awards data scripts.

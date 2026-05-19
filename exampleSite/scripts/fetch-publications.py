#!/usr/bin/env python3
"""
Bootstrap data/publications.yaml from Google Scholar or ORCID.

Given either a Google Scholar profile URL or an ORCID identifier, this
script enumerates the author's works, resolves each to a DOI, and prints
(or appends) YAML entries shaped like:

  - doi: "10.xxxx/yyyy"
    featured: false
    description: "<work title>"

Downstream, scripts/build-publications.py consumes that YAML to write
Hugo content pages.

Usage (run from the site root):
    python scripts/fetch-publications.py --orcid 0000-0000-0000-0000
    python scripts/fetch-publications.py --gs "https://scholar.google.com/citations?user=XXXX"
    python scripts/fetch-publications.py --orcid <id> --out data/publications.yaml
    python scripts/fetch-publications.py --orcid <id> --out data/publications.yaml --interactive

With --out:
  * If the file does not exist, the YAML is written there.
  * If the file exists, it must already be a list-of-DOI-entries YAML;
    new entries are appended (deduped by DOI), preserving existing
    comments and curation verbatim.
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install -r scripts/requirements.txt")

try:
    import requests
except ImportError:
    sys.exit("requests is required: pip install -r scripts/requirements.txt")


SITE_ROOT = Path(__file__).resolve().parent.parent
USER_AGENT = "hugo-azulprint/1.0 (mailto:contact@example.com)"

ORCID_WORKS_URL = "https://pub.orcid.org/v3.0/{orcid}/works"
CROSSREF_QUERY_URL = "https://api.crossref.org/works"
DOI_URL_RE = re.compile(r"^https?://(?:dx\.)?doi\.org/(?P<doi>.+)$", re.IGNORECASE)
ORCID_RE = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def warn(msg: str) -> None:
    print(f"warn: {msg}", file=sys.stderr)


# ───────────────────────── ORCID ─────────────────────────


def normalize_orcid(raw: str) -> str:
    s = raw.strip()
    s = re.sub(r"^https?://orcid\.org/", "", s, flags=re.IGNORECASE)
    if not ORCID_RE.match(s):
        sys.exit(f"invalid ORCID {raw!r}: expected dddd-dddd-dddd-dddX")
    return s


def fetch_orcid_works(orcid: str) -> list[tuple[str, str]]:
    """Return [(doi, title), ...] for the ORCID profile. Skips works without a DOI."""
    url = ORCID_WORKS_URL.format(orcid=orcid)
    resp = requests.get(
        url,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        timeout=30,
    )
    if resp.status_code == 404:
        sys.exit(f"ORCID has no record for {orcid!r}.")
    resp.raise_for_status()
    payload = resp.json()

    out: list[tuple[str, str]] = []
    for group in payload.get("group") or []:
        summaries = group.get("work-summary") or []
        if not summaries:
            continue
        ws = summaries[0]
        title = ((ws.get("title") or {}).get("title") or {}).get("value") or ""
        title = title.strip()
        ext_ids = ((ws.get("external-ids") or {}).get("external-id")) or []
        doi = None
        for ext in ext_ids:
            if (ext.get("external-id-type") or "").lower() == "doi":
                doi = (ext.get("external-id-value") or "").strip()
                if doi:
                    break
        if not doi:
            warn(f"no DOI for {title!r}")
            continue
        out.append((doi, title))
    return out


# ───────────────────────── Google Scholar ─────────────────────────


def parse_gs_user_id(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    user = qs.get("user", [None])[0]
    if not user:
        sys.exit(f"could not find user= parameter in Google Scholar URL {url!r}")
    return user


def crossref_doi_for_title(title: str) -> str | None:
    """Best-effort title→DOI via CrossRef bibliographic search."""
    if not title:
        return None
    params = {"query.bibliographic": title, "rows": "1"}
    resp = requests.get(
        CROSSREF_QUERY_URL,
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=20,
    )
    time.sleep(0.1)
    if not resp.ok:
        return None
    items = ((resp.json().get("message") or {}).get("items")) or []
    if not items:
        return None
    cand = items[0]
    cand_titles = cand.get("title") or []
    cand_title = cand_titles[0] if cand_titles else ""
    ratio = difflib.SequenceMatcher(
        None, title.strip().lower(), cand_title.strip().lower()
    ).ratio()
    if ratio < 0.85:
        return None
    return cand.get("DOI")


def fetch_gs_works(profile_url: str) -> list[tuple[str, str]]:
    try:
        from scholarly import scholarly
    except ImportError:
        sys.exit("scholarly is required for --gs: pip install -r scripts/requirements.txt")

    user_id = parse_gs_user_id(profile_url)
    log(f"fetching Google Scholar profile {user_id}…")
    author = scholarly.search_author_id(user_id)
    scholarly.fill(author, sections=["publications"])

    out: list[tuple[str, str]] = []
    pubs = author.get("publications") or []
    log(f"found {len(pubs)} publications on profile")
    for pub in pubs:
        scholarly.fill(pub)
        title = ((pub.get("bib") or {}).get("title") or "").strip()
        pub_url = pub.get("pub_url") or ""

        doi: str | None = None
        m = DOI_URL_RE.match(pub_url)
        if m:
            doi = m.group("doi").strip()
        if not doi:
            doi = crossref_doi_for_title(title)
        if not doi:
            warn(f"no DOI for {title!r}")
            continue
        out.append((doi, title))
    return out


# ───────────────────────── YAML emit ─────────────────────────


def build_entries(
    works: Iterable[tuple[str, str]], interactive: bool
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for doi, title in works:
        featured = False
        if interactive:
            log(f"\n{title}\n  doi: {doi}")
            answer = input("Feature this? [y/N] ").strip().lower()
            featured = answer.startswith("y")
        entries.append({"doi": doi, "featured": featured, "description": title})
    return entries


def render_yaml(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return ""
    dumped = yaml.safe_dump(
        entries, sort_keys=False, allow_unicode=True, width=1000
    )
    # Insert a blank line between top-level list items so the output
    # matches the existing data/publications.yaml style.
    parts = re.split(r"(?m)^- ", dumped)
    head, rest = parts[0], parts[1:]
    blocks = [f"- {chunk.rstrip()}" for chunk in rest]
    body = "\n\n".join(blocks)
    return (head + body + "\n") if body else dumped


def load_existing_dois(path: Path) -> set[str]:
    """Parse `path` as a list-of-DOI-entries YAML and return a lowercased DOI set."""
    text = path.read_text()
    try:
        parsed = yaml.safe_load(text)
    except yaml.YAMLError as e:
        sys.exit(f"{path}: failed to parse as YAML ({e}). Aborting.")
    if parsed is None:
        return set()
    if not isinstance(parsed, list):
        sys.exit(f"{path}: expected a YAML list of DOI entries at the top level.")
    dois: set[str] = set()
    for i, entry in enumerate(parsed):
        if not isinstance(entry, dict) or "doi" not in entry:
            sys.exit(f"{path}: entry #{i} is not a dict with a `doi` key: {entry!r}")
        doi = str(entry["doi"]).strip().lower()
        if doi:
            dois.add(doi)
    return dois


# ───────────────────────── main ─────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--gs", metavar="URL", help="Google Scholar profile URL")
    src.add_argument("--orcid", metavar="ID", help="ORCID identifier or URL")
    ap.add_argument(
        "--out",
        type=Path,
        help="Write/append YAML to this file. If omitted, writes to stdout.",
    )
    ap.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt y/N to set `featured` for each work.",
    )
    args = ap.parse_args()

    # Validate --out up front so a malformed target file fails before any
    # network work.
    existing_dois: set[str] | None = None
    if args.out and args.out.exists():
        existing_dois = load_existing_dois(args.out)

    if args.orcid:
        works = fetch_orcid_works(normalize_orcid(args.orcid))
    else:
        works = fetch_gs_works(args.gs)

    if not works:
        log("no works with DOIs found.")
        return 0

    if existing_dois is not None:
        before = len(works)
        works = [(d, t) for (d, t) in works if d.strip().lower() not in existing_dois]
        skipped = before - len(works)
        if skipped:
            log(f"skipped {skipped} entry/entries already present in {args.out}")
        if not works:
            log("nothing new to append.")
            return 0

    entries = build_entries(works, interactive=args.interactive)
    rendered = render_yaml(entries)

    if args.out:
        if args.out.exists():
            existing_text = args.out.read_text()
            sep = "" if existing_text.endswith("\n") else "\n"
            with args.out.open("a") as f:
                f.write(f"{sep}\n{rendered}")
            log(f"appended {len(entries)} entry/entries to {args.out}")
        else:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(rendered)
            log(f"wrote {len(entries)} entry/entries to {args.out}")
    else:
        sys.stdout.write(rendered)

    return 0


if __name__ == "__main__":
    sys.exit(main())

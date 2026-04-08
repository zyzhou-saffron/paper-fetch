#!/usr/bin/env python3
"""Fetch legal open-access PDFs by DOI.

Resolution order: Unpaywall -> Semantic Scholar openAccessPdf ->
arXiv -> PMC OA -> bioRxiv/medRxiv.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import os

EMAIL = os.environ.get("UNPAYWALL_EMAIL", "").strip()
UA = f"paper-fetch/0.1 (mailto:{EMAIL or 'anonymous'})"
TIMEOUT = 30


def _get(url: str, accept: str = "application/json") -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def _get_json(url: str):
    return json.loads(_get(url).decode("utf-8"))


def _download(url: str, dest: Path) -> bool:
    try:
        data = _get(url, accept="application/pdf")
    except Exception as e:
        print(f"  download failed: {e}", file=sys.stderr)
        return False
    if not data[:5].startswith(b"%PDF"):
        print("  response was not a PDF", file=sys.stderr)
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return True


def _slug(s: str, n: int = 40) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    return s[:n]


def _filename(meta: dict) -> str:
    author = _slug((meta.get("author") or "unknown").split()[-1], 20)
    year = str(meta.get("year") or "nd")
    title = _slug(meta.get("title") or "paper", 40)
    return f"{author}_{year}_{title}.pdf"


def try_unpaywall(doi: str) -> tuple[str | None, dict]:
    url = f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}?email={EMAIL}"
    try:
        d = _get_json(url)
    except Exception as e:
        print(f"[unpaywall] error: {e}", file=sys.stderr)
        return None, {}
    meta = {
        "title": d.get("title"),
        "year": d.get("year"),
        "author": (d.get("z_authors") or [{}])[0].get("family") if d.get("z_authors") else None,
    }
    loc = d.get("best_oa_location") or {}
    return loc.get("url_for_pdf"), meta


def try_semantic_scholar(doi: str) -> tuple[str | None, dict, dict]:
    url = (
        f"https://api.semanticscholar.org/graph/v1/paper/DOI:{urllib.parse.quote(doi)}"
        "?fields=title,year,authors,openAccessPdf,externalIds"
    )
    try:
        d = _get_json(url)
    except Exception as e:
        print(f"[s2] error: {e}", file=sys.stderr)
        return None, {}, {}
    meta = {
        "title": d.get("title"),
        "year": d.get("year"),
        "author": (d.get("authors") or [{}])[0].get("name"),
    }
    pdf = (d.get("openAccessPdf") or {}).get("url")
    return pdf, meta, d.get("externalIds") or {}


def try_arxiv(arxiv_id: str) -> str:
    return f"https://arxiv.org/pdf/{arxiv_id}.pdf"


def try_pmc(pmcid: str) -> str:
    pmcid = pmcid if pmcid.startswith("PMC") else f"PMC{pmcid}"
    return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/"


def try_biorxiv(doi: str) -> str | None:
    if not doi.startswith("10.1101/"):
        return None
    for server in ("biorxiv", "medrxiv"):
        try:
            d = _get_json(f"https://api.biorxiv.org/details/{server}/{doi}")
            coll = d.get("collection") or []
            if coll:
                latest = coll[-1]
                return f"https://www.{server}.org/content/10.1101/{latest['doi'].split('/')[-1]}v{latest.get('version', 1)}.full.pdf"
        except Exception:
            continue
    return None


def fetch(doi: str, out_dir: Path) -> bool:
    doi = doi.strip().removeprefix("https://doi.org/").removeprefix("doi.org/")
    print(f"==> {doi}")

    pdf_url, meta = try_unpaywall(doi)
    source = "unpaywall"

    if not pdf_url:
        pdf_url, s2_meta, ext = try_semantic_scholar(doi)
        meta = meta or s2_meta
        source = "semantic_scholar"
        if not pdf_url and ext.get("ArXiv"):
            pdf_url, source = try_arxiv(ext["ArXiv"]), "arxiv"
        if not pdf_url and ext.get("PubMedCentral"):
            pdf_url, source = try_pmc(ext["PubMedCentral"]), "pmc"

    if not pdf_url:
        pdf_url = try_biorxiv(doi)
        if pdf_url:
            source = "biorxiv"

    if not pdf_url:
        print(f"  no OA PDF found. metadata: {meta}", file=sys.stderr)
        return False

    dest = out_dir / _filename(meta or {"title": doi})
    print(f"  [{source}] {pdf_url}")
    if _download(pdf_url, dest):
        print(f"  saved -> {dest}")
        return True
    return False


def main():
    if not EMAIL:
        print("error: set UNPAYWALL_EMAIL env var to your contact email", file=sys.stderr)
        sys.exit(2)
    ap = argparse.ArgumentParser()
    ap.add_argument("doi", nargs="?")
    ap.add_argument("--batch", help="file with one DOI per line")
    ap.add_argument("--out", default="pdfs")
    args = ap.parse_args()

    out_dir = Path(args.out)
    dois = []
    if args.batch:
        dois = [l.strip() for l in Path(args.batch).read_text().splitlines() if l.strip()]
    elif args.doi:
        dois = [args.doi]
    else:
        ap.error("provide a DOI or --batch file")

    ok = sum(fetch(d, out_dir) for d in dois)
    print(f"\n{ok}/{len(dois)} succeeded")
    sys.exit(0 if ok == len(dois) else 1)


if __name__ == "__main__":
    main()

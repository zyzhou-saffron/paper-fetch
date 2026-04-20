"""Semantic Scholar 学术文献搜索模块。"""

import json
import os
import sys
import urllib.request
import urllib.parse

S2_API_BASE = "https://api.semanticscholar.org/graph/v1"
S2_SEARCH_URL = f"{S2_API_BASE}/paper/search"
S2_PAPER_URL = f"{S2_API_BASE}/paper"

SEARCH_FIELDS = (
    "paperId,title,abstract,year,citationCount,referenceCount,"
    "authors,journal,externalIds,url,venue,publicationDate,tldr"
)
CITATION_FIELDS = (
    "paperId,title,year,citationCount,authors,journal,externalIds,url,venue"
)

__all__ = ["search_s2", "get_paper", "get_citations", "get_references"]

def _get_api_key():
    return os.environ.get("SEMANTIC_SCHOLAR_API_KEY")

def _make_request(url, params=None):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    headers = {"Accept": "application/json"}
    api_key = _get_api_key()
    if api_key:
        headers["x-api-key"] = api_key
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("[错误] API 速率限制，请稍后重试或设置 SEMANTIC_SCHOLAR_API_KEY 环境变量", file=sys.stderr)
        else:
            print(f"[错误] HTTP {e.code}: {e.reason}", file=sys.stderr)
        return {}
    except urllib.error.URLError as e:
        print(f"[错误] 无法连接 Semantic Scholar API: {e}", file=sys.stderr)
        return {}

def _extract_doi(paper):
    ext_ids = paper.get("externalIds") or {}
    return ext_ids.get("DOI", "")

def _extract_authors(paper, max_count=20):
    authors = paper.get("authors") or []
    return [a.get("name", "") for a in authors[:max_count]]

def search_s2(
    query,
    limit=10,
    sort="relevance",
    year_from=None,
    year_to=None,
    fields_of_study=None,
    open_access_only=False,
    full_abstract=False,
):
    actual_limit = min(limit, 100) if limit is not None else 100
    params = {
        "query": query,
        "limit": actual_limit,
        "fields": SEARCH_FIELDS,
    }
    if year_from or year_to:
        year_str = f"{year_from or ''}-{year_to or ''}"
        params["year"] = year_str
    if sort == "citationCount":
        params["sort"] = "citationCount:desc"
    elif sort == "publicationDate":
        params["sort"] = "publicationDate:desc"
    if fields_of_study:
        params["fieldsOfStudy"] = fields_of_study
    if open_access_only:
        params["openAccessPdf"] = ""

    data = _make_request(S2_SEARCH_URL, params)
    results = []
    for paper in data.get("data", []):
        doi = _extract_doi(paper)
        abstract = (paper.get("abstract") or "")
        tldr = ((paper.get("tldr") or {}).get("text", ""))
        journal_info = paper.get("journal") or {}
        journal_name = journal_info.get("name", "") or paper.get("venue", "")

        results.append({
            "title": paper.get("title", ""),
            "doi": doi,
            "url": paper.get("url", ""),
            "authors": _extract_authors(paper),
            "year": paper.get("year"),
            "journal": journal_name,
            "cited_by_count": paper.get("citationCount", 0),
            "reference_count": paper.get("referenceCount", 0),
            "abstract": abstract if full_abstract else abstract[:500],
            "tldr": tldr,
            "source_db": "semantic_scholar",
            "oa_status": None,
            "paper_id": paper.get("paperId", ""),
            "publication_date": paper.get("publicationDate", ""),
        })
    if limit is not None:
        return results[:limit]
    return results

def get_paper(paper_id, full_abstract=False):
    url = f"{S2_PAPER_URL}/{urllib.parse.quote(paper_id, safe='')}"
    params = {"fields": SEARCH_FIELDS}
    paper = _make_request(url, params)
    if not paper: return None
    doi = _extract_doi(paper)
    abstract = (paper.get("abstract") or "")
    tldr = ((paper.get("tldr") or {}).get("text", ""))
    journal_info = paper.get("journal") or {}
    journal_name = journal_info.get("name", "") or paper.get("venue", "")
    return {
        "title": paper.get("title", ""),
        "doi": doi,
        "url": paper.get("url", ""),
        "authors": _extract_authors(paper, max_count=20),
        "year": paper.get("year"),
        "journal": journal_name,
        "cited_by_count": paper.get("citationCount", 0),
        "reference_count": paper.get("referenceCount", 0),
        "abstract": abstract if full_abstract else abstract[:500],
        "tldr": tldr,
        "source_db": "semantic_scholar",
        "oa_status": None,
        "paper_id": paper.get("paperId", ""),
        "publication_date": paper.get("publicationDate", ""),
    }

def get_citations(paper_id, limit=20):
    url = f"{S2_PAPER_URL}/{urllib.parse.quote(paper_id, safe='')}/citations"
    actual_limit = min(limit, 100) if limit is not None else 100
    params = {"fields": CITATION_FIELDS, "limit": actual_limit}
    data = _make_request(url, params)
    results = []
    for item in data.get("data", []):
        paper = item.get("citingPaper", {})
        doi = _extract_doi(paper)
        journal_info = paper.get("journal") or {}
        results.append({
            "title": paper.get("title", ""),
            "doi": doi,
            "url": paper.get("url", ""),
            "authors": _extract_authors(paper),
            "year": paper.get("year"),
            "journal": journal_info.get("name", "") or paper.get("venue", ""),
            "cited_by_count": paper.get("citationCount", 0),
            "source_db": "semantic_scholar",
            "oa_status": None,
            "tldr": "",
            "abstract": "",
            "paper_id": paper.get("paperId", ""),
        })
    if limit is not None:
        return results[:limit]
    return results

def get_references(paper_id, limit=20):
    url = f"{S2_PAPER_URL}/{urllib.parse.quote(paper_id, safe='')}/references"
    actual_limit = min(limit, 100) if limit is not None else 100
    params = {"fields": CITATION_FIELDS, "limit": actual_limit}
    data = _make_request(url, params)
    results = []
    for item in data.get("data", []):
        paper = item.get("citedPaper", {})
        doi = _extract_doi(paper)
        journal_info = paper.get("journal") or {}
        results.append({
            "title": paper.get("title", ""),
            "doi": doi,
            "url": paper.get("url", ""),
            "authors": _extract_authors(paper),
            "year": paper.get("year"),
            "journal": journal_info.get("name", "") or paper.get("venue", ""),
            "cited_by_count": paper.get("citationCount", 0),
            "source_db": "semantic_scholar",
            "oa_status": None,
            "tldr": "",
            "abstract": "",
            "paper_id": paper.get("paperId", ""),
        })
    if limit is not None:
        return results[:limit]
    return results

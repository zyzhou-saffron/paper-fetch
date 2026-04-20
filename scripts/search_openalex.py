"""通用 OpenAlex 学术文献搜索模块。"""

import json
import os
import sys
import urllib.request
import urllib.parse

OPENALEX_API = "https://api.openalex.org/works"
MAILTO = os.environ.get("UNPAYWALL_EMAIL", "openclaw-agent@example.com")

__all__ = ["search", "format_table", "format_compact", "format_citation"]

def _build_filter(year_from, year_to, journal, author):
    filters = []
    if year_from:
        filters.append(f"from_publication_date:{year_from}-01-01")
    if year_to:
        filters.append(f"to_publication_date:{year_to}-12-31")
    return ",".join(filters) if filters else None

def _extract_doi(work):
    doi = work.get("doi", "") or ""
    if doi.startswith("https://doi.org/"):
        doi = doi[len("https://doi.org/"):]
    return doi

def _reconstruct_abstract(work):
    abstract_index = work.get("abstract_inverted_index")
    if not abstract_index:
        return ""
    word_positions = []
    for word, positions in abstract_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort()
    return " ".join(w for _, w in word_positions)

def search(
    query: str,
    limit: int | None = 10,
    sort: str = "relevance_score",
    year_from: int | None = None,
    year_to: int | None = None,
    journal: str | None = None,
    author: str | None = None,
    full_abstract: bool = False,
) -> list[dict]:
    # Use max page size or large enough fetch
    fetch_limit = min(limit * 3 if (limit and (journal or author)) else (limit or 50), 50) if limit else 100
    params = {
        "search": query,
        "per_page": fetch_limit,
        "mailto": MAILTO,
    }
    
    if sort != "relevance_score":
        params["sort"] = sort + ":desc"
        
    api_filter = _build_filter(year_from, year_to, journal=None, author=None)
    if api_filter:
        params["filter"] = api_filter
        
    url = f"{OPENALEX_API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        print(f"[错误] 无法连接 OpenAlex API: {e}", file=sys.stderr)
        return []
        
    results = []
    for work in data.get("results", []):
        authors = [
            (a.get("author") or {}).get("display_name", "")
            for a in work.get("authorships", [])
        ]
        doi = _extract_doi(work)
        abstract = _reconstruct_abstract(work)
        journal_name = (
            ((work.get("primary_location") or {}).get("source") or {})
            .get("display_name", "")
        )
        
        if journal and journal.lower() not in journal_name.lower():
            continue
            
        if author:
            author_lower = author.lower()
            if not any(author_lower in a.lower() for a in authors):
                continue
                
        results.append({
            "title": work.get("title", ""),
            "doi": doi,
            "url": f"https://doi.org/{doi}" if doi else work.get("id", ""),
            "authors": authors[:20],
            "year": work.get("publication_year"),
            "journal": journal_name,
            "cited_by_count": work.get("cited_by_count", 0),
            "abstract": abstract if full_abstract else abstract[:500],
            "source_db": "openalex",
            "tldr": "",
            "oa_status": None,
            "openalex_id": work.get("id", ""),
        })
        
    if limit is not None:
        return results[:limit]
    return results

def format_table(results: list[dict]) -> str:
    if not results:
        return "（无结果）"
    lines = []
    sep = "─" * 90
    for i, r in enumerate(results, 1):
        auth_list = r.get("authors") or []
        authors_str = ", ".join(auth_list[:3])
        if len(auth_list) > 3:
            authors_str += " et al."
        lines.append(sep)
        lines.append(f"[{i}] {r.get('title','')}")
        lines.append(f"    {authors_str} | {r.get('journal', '')} | {r.get('year', '')} | Cited: {r.get('cited_by_count', 0)}")
        lines.append(f"    DOI: {r.get('doi') or '—'}   {r.get('url', '')}")
        if r.get("tldr"):
            lines.append(f"    TLDR: {r['tldr']}")
        elif r.get("abstract"):
            abs_text = r.get("abstract", "")
            abstract_preview = abs_text[:120].replace("\\n", " ")
            if len(abs_text) > 120:
                abstract_preview += "..."
            lines.append(f"    摘要: {abstract_preview}")
        
        oa = r.get("oa_status")
        if oa is not None:
            color = "🟢" if r.get('oa_available') else "🔴"
            status_str = f"{color} OA Available ({oa})" if r.get('oa_available') else f"{color} Closed Access"
            lines.append(f"    {status_str}   📦 来源: {r.get('source_db', 'unknown')}")
        else:
            lines.append(f"    📦 来源: {r.get('source_db', 'unknown')}")
            
    lines.append(sep)
    return "\n".join(lines)

def format_compact(results: list[dict]) -> str:
    lines = []
    for r in results:
        auth_list = r.get("authors") or []
        authors_str = ", ".join(auth_list[:3])
        if len(auth_list) > 3:
            authors_str += " et al."
        lines.append(
            f"[{r.get('year', '')}] {r.get('title', '')} | {authors_str} | "
            f"{r.get('journal', '')} | DOI:{r.get('doi', '')} | Cited:{r.get('cited_by_count', '')}"
        )
    return "\n".join(lines)

def format_citation(results: list[dict], style: str = "nsfc") -> str:
    if not results:
        return "（无结果）"
    citations = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "")
        year = r.get("year", "")
        journal = r.get("journal", "")
        doi = r.get("doi", "")
        doi_url = f"https://doi.org/{doi}" if doi else ""
        authors_full = r.get("authors") or []
        
        if style == "apa":
            apa_authors = []
            for name in authors_full[:20]:
                parts = name.strip().split()
                if len(parts) >= 2:
                    last = parts[-1]
                    initials = ". ".join(p[0] for p in parts[:-1] if p) + "."
                    apa_authors.append(f"{last}, {initials}")
                else:
                    apa_authors.append(name)
            if len(authors_full) > 20:
                author_str = ", ".join(apa_authors[:19]) + ", ... " + apa_authors[-1]
            elif len(apa_authors) > 1:
                author_str = ", ".join(apa_authors[:-1]) + ", & " + apa_authors[-1]
            else:
                author_str = apa_authors[0] if apa_authors else ""
            parts_list = [author_str, f"({year})." if year else "", f"{title}." if title else ""]
            if journal:
                parts_list.append(f"*{journal}*.")
            if doi_url:
                parts_list.append(doi_url)
            citation = " ".join(p for p in parts_list if p)
        else:
            nsfc_authors = []
            for name in authors_full[:6]:
                parts = name.strip().split()
                if len(parts) >= 2:
                    last = parts[-1]
                    initials = "".join(p[0] for p in parts[:-1] if p)
                    nsfc_authors.append(f"{last} {initials}")
                else:
                    nsfc_authors.append(name)
            if len(authors_full) > 6:
                author_str = ", ".join(nsfc_authors) + ", et al."
            else:
                author_str = ", ".join(nsfc_authors)
            parts_list = [f"[{i}]", f"{author_str}." if author_str else "",
                          f"{title}.", f"{journal}," if journal else "", str(year) + "." if year else ""]
            if doi_url:
                parts_list.append(f"DOI: {doi_url}")
            citation = " ".join(p for p in parts_list if p)
        citations.append(citation)
    return "\n\n".join(citations)

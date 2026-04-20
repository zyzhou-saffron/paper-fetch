#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
"""Unified Academic Search and Download Orchestrator for paper-fetch."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Fix path to import modules
sys.path.insert(0, str(Path(__file__).parent))
try:
    from search_openalex import search as search_openalex, format_table, format_compact, format_citation
    from search_s2 import search_s2, get_paper, get_citations, get_references
    from fetch import fetch
except ImportError as e:
    print(f"Error importing modules: {e}", file=sys.stderr)
    sys.exit(1)

def _get_json(url: str, timeout: int = 10):
    import urllib.request
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def check_unpaywall(doi: str, email: str, timeout: int = 10) -> dict:
    url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
    try:
        data = _get_json(url, timeout=timeout)
        loc = data.get("best_oa_location") or {}
        pdf_url = loc.get("url_for_pdf")
        return {
            "oa_available": pdf_url is not None,
            "oa_url": pdf_url,
            "oa_status": data.get("oa_status", "unknown"),
        }
    except Exception:
        return {"oa_available": None, "oa_url": None, "oa_status": "unknown"}

def _merge_dedup(results: list[dict], prefer: str = "semantic_scholar") -> list[dict]:
    seen = {}
    for r in results:
        doi = r.get("doi")
        if not doi:
            # unique key for no-doi
            seen[id(r)] = r
            continue
        if doi in seen:
            existing = seen[doi]
            if not existing.get("tldr") and r.get("tldr"):
                existing["tldr"] = r["tldr"]
            if r.get("source_db") == prefer and existing.get("source_db") != prefer:
                r["tldr"] = r.get("tldr") or existing.get("tldr", "")
                r["source_db"] = f"{prefer} + openalex"
                seen[doi] = r
            else:
                existing["source_db"] = f"{existing.get('source_db', 'unknown')} + {r.get('source_db', 'unknown')}"
        else:
            seen[doi] = r.copy()
    return list(seen.values())

def unified_search(
    query: str,
    limit: int | None = 10,
    source: str = "auto",
    year_from: int | None = None,
    year_to: int | None = None,
    enrich_oa: bool = True,
    **kwargs,
) -> list[dict]:
    results = []
    if source in ("auto", "openalex"):
        results.extend(search_openalex(query, limit=limit, year_from=year_from, year_to=year_to, **kwargs))
    
    if source in ("auto", "s2"):
        s2_results = search_s2(query, limit=limit, year_from=year_from, year_to=year_to, **kwargs)
        results.extend(s2_results)

    if source == "auto":
        results = _merge_dedup(results)

    if enrich_oa:
        email = os.environ.get("UNPAYWALL_EMAIL", "")
        if email:
            print("Checking OA status from Unpaywall...", file=sys.stderr)
            for i, r in enumerate(results):
                if r.get("doi"):
                    time.sleep(0.1) # 100ms delay to avoid rate limit
                    oa_info = check_unpaywall(r["doi"], email)
                    r["oa_status"] = oa_info["oa_status"]
                    r["oa_available"] = oa_info["oa_available"]

    results.sort(key=lambda x: x.get("cited_by_count", 0), reverse=True)
    if limit is not None:
        return results[:limit]
    return results

def cmd_search(args):
    results = unified_search(
        args.query,
        limit=args.limit,
        source=args.source,
        year_from=args.year_from,
        year_to=args.year_to,
        enrich_oa=not args.no_oa_check
    )
    
    if args.doi_only:
        for r in results:
            if r.get("doi"):
                print(r["doi"])
        return
        
    fmt = args.format
    if fmt == "table":
        print(format_table(results))
    elif fmt == "compact":
        print(format_compact(results))
    elif fmt == "citation":
        print(format_citation(results, style=args.citation_style))
    else:
        print(json.dumps(results, ensure_ascii=False, indent=2))

def cmd_refs(args):
    is_citations = (args.command == "citations")
    func = get_citations if is_citations else get_references
    results = func(args.paper_id, limit=args.limit)
    
    if not args.no_oa_check:
        email = os.environ.get("UNPAYWALL_EMAIL", "")
        if email:
            print("Checking OA status from Unpaywall...", file=sys.stderr)
            for r in results:
                if r.get("doi"):
                    time.sleep(0.1) # delay
                    oa_info = check_unpaywall(r["doi"], email)
                    r["oa_status"] = oa_info["oa_status"]
                    r["oa_available"] = oa_info["oa_available"]
                    
    results.sort(key=lambda x: x.get("cited_by_count", 0), reverse=True)
    
    if args.doi_only:
        for r in results:
            if r.get("doi"):
                print(r["doi"])
        return
        
    if args.format == "table":
        print(format_table(results))
    elif args.format == "compact":
        print(format_compact(results))
    elif args.format == "citation":
        print(format_citation(results, style=args.citation_style))
    else:
        print(json.dumps(results, ensure_ascii=False, indent=2))

def cmd_grab(args, search_func_wrapper):
    results = search_func_wrapper()
    print(format_table(results), file=sys.stderr)
    
    dois = [r["doi"] for r in results if r.get("doi")]
    # If no-oa-check was NOT given, filter out those known to be closed access
    if not args.no_oa_check:
        dois = [r["doi"] for r in results if r.get("doi") and r.get("oa_available") is not False]
        
    if not dois:
        print("未找到带 DOI 或已知可访问的论文，无法下载。", file=sys.stderr)
        sys.exit(1)
        
    print(f"\n📥 开始下载 {len(dois)} 篇论文...\n", file=sys.stderr)
    download_results = []
    
    out_dir_path = Path(args.out)
    out_dir_path.mkdir(parents=True, exist_ok=True)
    
    for i, doi in enumerate(dois, 1):
        print(f"  [{i}/{len(dois)}] {doi}", file=sys.stderr)
        
        # Add a 1.2 second delay between requests to strictly respect Semantic Scholar's 
        # 1 request per second API limit during batch fetching
        if i > 1:
            time.sleep(1.2)
            
        try:
            result = fetch(
                doi,
                out_dir=out_dir_path,
                dry_run=args.dry_run,
                overwrite=False,
                timeout=30,
            )
            download_results.append(result)
            if result.get("success"):
                print(f"    ✅ {result.get('file', '?')}", file=sys.stderr)
            else:
                err = result.get("error", {})
                print(f"    ❌ {err.get('message', 'failed')}", file=sys.stderr)
        except Exception as e:
             print(f"    ❌ System error: {str(e)}", file=sys.stderr)
             
    succeeded = sum(1 for r in download_results if r.get("success"))
    print(f"\n📊 完成: {succeeded}/{len(dois)} 下载成功", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(
        description="Unified Academic Search and Download",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # search cmd
    parser_search = subparsers.add_parser("search", help="纯搜索，返回论文列表")
    parser_search.add_argument("query", help="搜索关键词")
    parser_search.add_argument("--source", choices=["auto", "openalex", "s2"], default="auto", help="数据源")
    parser_search.add_argument("--limit", type=int, default=10, help="最多返回数量 (留空则无限制, 0表示无限制)")
    parser_search.add_argument("--year-from", type=int, default=None)
    parser_search.add_argument("--year-to", type=int, default=None)
    parser_search.add_argument("--format", choices=["json", "compact", "table", "citation"], default="json")
    parser_search.add_argument("--citation-style", choices=["nsfc", "apa"], default="nsfc")
    parser_search.add_argument("--doi-only", action="store_true")
    parser_search.add_argument("--no-oa-check", action="store_true", help="跳过 Unpaywall 查询以加快速度")
    
    # grab cmd (search + download)
    parser_grab = subparsers.add_parser("grab", help="搜索 + 自动下载 OA PDF")
    parser_grab.add_argument("query", help="搜索关键词")
    parser_grab.add_argument("--source", choices=["auto", "openalex", "s2"], default="auto", help="数据源")
    parser_grab.add_argument("--limit", type=int, default=None, help="最多返回数量 (默认无限制)")
    parser_grab.add_argument("--year-from", type=int, default=None)
    parser_grab.add_argument("--year-to", type=int, default=None)
    parser_grab.add_argument("--out", default="pdfs", help="输出目录")
    parser_grab.add_argument("--dry-run", action="store_true", help="仅预览下载路径，不实际下载")
    parser_grab.add_argument("--no-oa-check", action="store_true", help="不检查OA状态直接尝试全部下载")

    # refs / citations cmd
    for cmd_name, help_text in [("refs", "查看参考文献列表"), ("citations", "查看引用者")]:
        p = subparsers.add_parser(cmd_name, help=help_text)
        p.add_argument("paper_id", help="如 DOI:xxx")
        p.add_argument("--limit", type=int, default=20, help="限制数量")
        p.add_argument("--format", choices=["json", "compact", "table", "citation"], default="json")
        p.add_argument("--citation-style", choices=["nsfc", "apa"], default="nsfc")
        p.add_argument("--doi-only", action="store_true")
        p.add_argument("--no-oa-check", action="store_true", help="跳过 Unpaywall 查询")

    # grab-refs / grab-citations cmd
    for cmd_name, help_text in [("grab-refs", "下载参考文献 PDF"), ("grab-citations", "下载引用者 PDF")]:
        p = subparsers.add_parser(cmd_name, help=help_text)
        p.add_argument("paper_id", help="如 DOI:xxx")
        p.add_argument("--limit", type=int, default=None, help="限制数量")
        p.add_argument("--out", default="pdfs", help="输出目录")
        p.add_argument("--dry-run", action="store_true")
        p.add_argument("--no-oa-check", action="store_true", help="不检查OA状态")
        
    args = parser.parse_args()
    
    # Process limit argument if missing or 0 to None
    if getattr(args, "limit", None) == 0:
        args.limit = None

    if args.command == "search":
        cmd_search(args)
    elif args.command in ("refs", "citations"):
        cmd_refs(args)
    elif args.command == "grab":
        cmd_grab(args, lambda: unified_search(
            args.query,
            limit=args.limit,
            source=args.source,
            year_from=args.year_from,
            year_to=args.year_to,
            enrich_oa=not args.no_oa_check
        ))
    elif args.command in ("grab-refs", "grab-citations"):
        is_citations = (args.command == "grab-citations")
        func = get_citations if is_citations else get_references
        def grab_refs_wrapper():
            results = func(args.paper_id, limit=args.limit)
            if not args.no_oa_check:
                email = os.environ.get("UNPAYWALL_EMAIL", "")
                if email:
                    print("Checking OA status from Unpaywall...", file=sys.stderr)
                    for r in results:
                        if r.get("doi"):
                            time.sleep(0.1)
                            oa_info = check_unpaywall(r["doi"], email)
                            r["oa_status"] = oa_info["oa_status"]
                            r["oa_available"] = oa_info["oa_available"]
            results.sort(key=lambda x: x.get("cited_by_count", 0), reverse=True)
            return results
        cmd_grab(args, grab_refs_wrapper)

if __name__ == "__main__":
    main()

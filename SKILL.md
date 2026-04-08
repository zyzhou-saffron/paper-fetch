---
name: paper-fetch
description: Use when the user wants to download a paper PDF from a DOI, title, or URL via legal open-access sources. Tries Unpaywall, arXiv, bioRxiv/medRxiv, PubMed Central, and Semantic Scholar in order. Never uses Sci-Hub or paywall bypass.
homepage: https://github.com/Agents365-ai/paper-fetch
metadata: {"openclaw":{"requires":{"bins":["python3"],"env":["UNPAYWALL_EMAIL"]},"emoji":"📄"}}
---

# paper-fetch

Fetch the legal open-access PDF for a paper given a DOI (or title). Tries multiple OA sources in priority order and stops at the first hit.

## Resolution order

1. **Unpaywall** — `https://api.unpaywall.org/v2/{doi}?email=$UNPAYWALL_EMAIL`, read `best_oa_location.url_for_pdf`
2. **Semantic Scholar** — `https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=openAccessPdf,externalIds`
3. **arXiv** — if `externalIds.ArXiv` present, `https://arxiv.org/pdf/{arxiv_id}.pdf`
4. **PubMed Central OA** — if PMCID present, `https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/`
5. **bioRxiv / medRxiv** — if DOI prefix is `10.1101`, use the `claude_ai_bioRxiv` MCP `get_preprint` tool, then fetch the PDF URL
6. Otherwise → report failure with title/authors so the user can request via ILL

If only a title is given, resolve to a DOI first via Semantic Scholar `search_paper_by_title` (asta MCP) or Crossref.

## Usage

Run the helper script:

```bash
python scripts/fetch.py <DOI> [--out DIR]
```

Default output directory: `./pdfs/`. Filenames: `{first_author}_{year}_{short_title}.pdf`.

The script prints the source that succeeded (e.g. `[unpaywall] saved to pdfs/Smith_2023_attention.pdf`) or a structured failure with the metadata it did find.

## Notes

- Unpaywall requires a contact email in every request. Set it once: `export UNPAYWALL_EMAIL=you@example.com` (e.g. in `~/.zshrc`). The script exits with an error if it's not set.
- Never attempts to bypass paywalls. If no OA copy exists, the skill reports failure — do not suggest Sci-Hub or similar.
- For bulk jobs, pass a file of DOIs: `python scripts/fetch.py --batch dois.txt`.
